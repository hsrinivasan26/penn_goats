"""
mcq_engine.py
PENN GOATS - financial-literacy multiple-choice quiz engine.

WHAT THIS DOES (in order):
  1. Holds the MCQ-generation prompt as a plain string (MCQ_GENERATION_PROMPT).
  2. Sends that string to an AI model to generate a JSON question bank.
  3. Parses + validates the JSON into typed objects (QuestionBank / MCQItem).
  4. Presents the quiz and PROMPTS THE USER for answers, then scores them.

It is deliberately UI-friendly: every step is a plain function or dataclass with no
hidden I/O, so a web / GUI front end can drive it
(build_prompt -> generate_bank -> Quiz.submit_answer) without touching the CLI.
A ready-made interactive CLI (run_cli_quiz) is included for quick local testing.

Dependencies: standard library only. The Gemini adapter imports `google.genai`
lazily (same SDK as game/ai.py), so you only need that package when you call the model.
"""

from __future__ import annotations

import json
import random
import re
from dataclasses import asdict, dataclass, field
from typing import Callable, Optional

# ======================================================================================
# 1) THE PROMPT  (this is the string sent to the AI model, before any user interaction)
# ======================================================================================
# IMPORTANT: this is a plain string, NOT an f-string. The JSON examples below contain
# literal { } braces that must be preserved exactly, so do not add an `f` prefix.
MCQ_GENERATION_PROMPT = """<role>
You are a financial-literacy assessment designer and professional item writer. You create
rigorous, unambiguous multiple-choice questions (MCQs) for a personal-finance simulation
game aimed at young adults (ages ~17-29) in the United States. Each question both teaches
and assesses a real financial concept, using either a plain-concept framing or an in-game
scenario framing. Make it python and UI friendly
</role>

<configuration>
Use these settings (defaults shown; the caller may override them):
- questions_per_subtopic: 5        # produce 1 easy + 1 medium + 1 hard for each subtopic
- framing_mix: ~50% concept, ~50% scenario (across the whole bank)
- audience: United States young adults; reading level grade 8-10
- currency: USD
- scope: ALL categories in <topic_taxonomy>   # to shard, set this to ONE category name
</configuration>

<task>
Generate an MCQ bank that comprehensively assesses the concepts in <topic_taxonomy>.
Cover EVERY subtopic in scope at the requested count and difficulty spread. Return the
result as a single JSON object that exactly matches <output_format> and obeys every rule
in <item_rules> and <output_discipline>.
</task>

<topic_taxonomy>
Each category has a CODE (used in item ids) and a list of subtopics. The game_phase in
brackets links the concept to the game's turn structure.

A. INCOME - code INC  [Phase 1: Income]
   - getting-hired: pay scales with a job's difficulty/skill and your education + experience
   - gross-vs-net: gross pay vs. net (take-home) pay
   - withholdings: Federal income tax, State income tax, and FICA (Social Security + Medicare)
   - paystub-literacy: reading a paystub and its deductions
   - career-growth: education/experience unlock higher-paying jobs and raises over time
   - income-risk: losing income to layoffs or a company going bankrupt

B. INVESTING - code INV  [Phase 2: Markets]
   - risk-return: the core trade-off between risk and expected return
   - savings: risk-free savings (low risk, low return)
   - index-funds: diversified funds (medium risk, medium return)
   - stocks: individual stocks (high risk/return, volatility)
   - crypto: crypto (very high risk; danger of over-allocation)
   - real-estate: home equity / property (slow appreciation, illiquid)
   - realized-vs-unrealized: value changes on paper vs. cash realized only when you sell
   - diversification: spreading money across asset classes to manage risk
   - volatility-downturns: markets can fall; sequencing and timing risk
   - compounding: growth compounding over many turns/years

C. TAXES - code TAX  [Phase 5: Events]
   - progressive-brackets: progressive income tax; marginal vs. effective rate
   - capital-gains: tax charged on the PROFIT when investments are sold
   - annual-reconciliation: yearly tax bill vs. what was already withheld from paychecks

D. DEBT & CREDIT - code DEBT  [Phase 3: Interest & liabilities / Phase 4: Outflows]
   - student-loans: interest accrual; repayment (with interest) begins after graduation
   - college-choice: public vs. private university - cost vs. potential reward
   - mortgage-vs-rent: buy with a mortgage (monthly payment) vs. pay flat-rate rent
   - credit-cards: highest interest rate; minimum payments; revolving-debt spiral
   - interest-mechanics: how interest makes balances grow; principal vs. interest
   - minimum-payments: required monthly debt outflows and what happens if you miss them

E. BUDGETING & CASH FLOW - code BUD  [Phase 4: Forced outflows]
   - essentials: required outflows (housing, food, transport, utilities)
   - needs-vs-wants: distinguishing mandatory bills from discretionary spending
   - shortfall: spending more than available cash pushes the gap into debt (shortfall flag)
   - liquidity-emergency: keeping accessible cash / an emergency fund

F. NET WORTH & GOALS - code NW  [Phase 8: Win check]
   - net-worth-formula: Net Worth = (cash + investments) - liabilities
   - bankruptcy: losing when net worth falls to 0 or below
   - goal-target: saving toward a target net worth by the final turn

G. WELLBEING & BEHAVIOR - code WELL  [Phase 7: Happiness]
   - leisure-happiness: discretionary/leisure spending raises happiness
   - burnout: happiness decays; hitting 0 ends the game; work-life balance
   - lifestyle-inflation: spending rising with income; the save-vs-spend trade-off

H. RISK & LIFE EVENTS - code RISK  [Phase 5: Events]
   - life-events: random events (car repair, medical bill, layoff, windfall, raise)
   - probability-ev: probability and expected-value thinking about uncertain outcomes
   - preparedness: insurance / buffers that soften negative shocks
</topic_taxonomy>

<output_format>
Return exactly ONE JSON object with this structure (field dictionary below; the real
output must be valid JSON with NO comments):

Top level:
- "bank_metadata": object with "audience" (string), "currency" (string),
  "generated_for" (string), "total_items" (integer), "difficulty_scale"
  (array: ["easy","medium","hard"]).
- "items": array of item objects (see below).
- "coverage_manifest": object mapping each category CODE -> object mapping each subtopic
  slug -> array of the item ids that assess it.
- "self_check": object with booleans "every_in_scope_subtopic_covered",
  "each_item_has_exactly_one_correct_option", "all_items_have_4_to_6_options", and a
  "notes" string (record any assumptions or gaps).

Each item object:
- "id": string, format "<CODE>-<subtopic-slug>-<3-digit>", e.g. "TAX-capital-gains-001".
- "category": string, one of the 8 category names.
- "subtopic": string, a subtopic slug from <topic_taxonomy>.
- "game_phase": string (the bracketed phase) or null.
- "framing": string, "concept" or "scenario".
- "difficulty": string, "easy" | "medium" | "hard".
- "bloom_level": string, "recall" | "understand" | "apply" | "analyze".
- "stem": string, the question text (self-contained).
- "options": array of 4 to 6 objects (option ids "A"-"F"), each:
    { "id": "A"|"B"|"C"|"D"|"E"|"F", "text": string, "is_correct": boolean,
      "distractor_rationale": string }   // for the correct option, use "correct answer"
- "correct_option_id": string, "A" | "B" | "C" | "D" | "E" | "F" (exactly one option is_correct=true).
- "explanation": string, 1-3 sentences teaching why the answer is right.
- "misconception_tags": array of short strings naming the misconception each distractor targets.
- "learning_objective": string, one sentence.
</output_format>

<item_rules>
1. RANDOM amount of options from 4-6 (A-F); exactly ONE is correct make sure its a random letter between A-F.
2. Exactly one defensibly-best answer. Every distractor must be plausible and target a
   SPECIFIC named misconception (state it in distractor_rationale and misconception_tags).
3. No "All of the above" / "None of the above". Avoid negative stems ("which is NOT")
   unless the NOT is capitalized and the item truly needs it.
4. Keep options parallel in length and grammar; do not make the correct answer the longest.
5. Vary the position of the correct answer across items (do not default to B)
6. Try to have at least one question with more than 4 options.
7. Items are self-contained: include any numbers needed in the stem; never reference
   another question.
8. Use realistic but FICTIONAL figures. For stocks/crypto/funds use generic or invented
   names ("a crypto token", "a broad index fund", "Fund X") - never real tickers, and
   never give buy/sell or personalized financial advice. Assess knowledge, not decisions.
9. US context. Spell out an acronym on first use in a stem when it aids clarity
   (e.g., "FICA (Social Security and Medicare tax)").
10. Difficulty calibration:
    - easy   = recall/definition (recall/understand).
    - medium = single-step application (apply).
    - hard   = multi-step reasoning or a trade-off/comparison (apply/analyze), e.g. compute
      net pay from gross, distinguish marginal vs. effective rate, compare rent vs. mortgage.
11. framing="scenario" items use the game world - a character with a job; the four sliders
    (cash, investments, liabilities, happiness); a turn = one month; annual tax at year-end
    - but must remain solvable from the stem alone.
12. explanation should teach the concept and briefly note why the key distractors are wrong.
13. Honor questions_per_subtopic and the difficulty spread for every in-scope subtopic.
</item_rules>

<examples>
Reference items showing the required format and quality. Do NOT copy these verbatim.

{
  "id": "INC-gross-vs-net-002",
  "category": "INCOME",
  "subtopic": "gross-vs-net",
  "game_phase": "Phase 1: Income",
  "framing": "concept",
  "difficulty": "medium",
  "bloom_level": "understand",
  "stem": "Maya's job lists a gross salary of $48,000 per year. What does her 'net pay' refer to?",
  "options": [
    { "id": "A", "text": "The full $48,000, because that is her salary.", "is_correct": false, "distractor_rationale": "Treats gross pay as take-home; ignores withholdings." },
    { "id": "B", "text": "What is left after taxes and other withholdings are subtracted from gross pay.", "is_correct": true, "distractor_rationale": "correct answer" },
    { "id": "C", "text": "Her salary plus any bonuses, measured before taxes.", "is_correct": false, "distractor_rationale": "Describes a larger gross figure, not net." },
    { "id": "D", "text": "Only the amount withheld for Social Security and Medicare.", "is_correct": false, "distractor_rationale": "Confuses net pay with the FICA deduction itself." }
  ],
  "correct_option_id": "B",
  "explanation": "Net (take-home) pay is gross pay minus withholdings such as federal, state, and FICA taxes. Gross is the headline salary; net is what actually lands in your account.",
  "misconception_tags": ["gross-vs-net confusion", "net equals FICA"],
  "learning_objective": "Distinguish gross pay from net (take-home) pay."
}

{
  "id": "TAX-capital-gains-003",
  "category": "TAXES",
  "subtopic": "capital-gains",
  "game_phase": "Phase 5: Events",
  "framing": "scenario",
  "difficulty": "hard",
  "bloom_level": "apply",
  "stem": "It is turn 30. Devon sells a crypto token for $3,000 that he originally bought for $2,000. The game charges capital-gains tax only on the profit, at 15%. How much tax is added to his liabilities from this sale?",
  "options": [
    { "id": "A", "text": "$150", "is_correct": true, "distractor_rationale": "correct answer" },
    { "id": "B", "text": "$10", "is_correct": false, "distractor_rationale": "correct answer" },
    { "id": "C", "text": "$300", "is_correct": false, "distractor_rationale": "Taxes the $2,000 cost basis instead of the gain." },
    { "id": "D", "text": "$450", "is_correct": false, "distractor_rationale": "Taxes the full $3,000 of proceeds, not the profit." },
    { "id": "E", "text": "$0, because selling just moves value into cash.", "is_correct": false, "distractor_rationale": "Assumes selling is untaxed; selling realizes a taxable gain." }
  ],
  "correct_option_id": "A",
  "explanation": "Capital-gains tax applies to the profit: proceeds ($3,000) minus cost basis ($2,000) = $1,000 gain; 15% of $1,000 = $150.",
  "misconception_tags": ["taxing proceeds not gain", "taxing basis not gain", "selling is non-taxable"],
  "learning_objective": "Compute capital-gains tax on the realized profit from selling an investment."
}
</examples>

<output_discipline>
- Output ONLY the JSON object. No preamble, no explanation, no markdown code fences, and
  no text before or after the JSON.
- The JSON must be valid: double-quoted keys and strings, no trailing commas, no comments,
  no NaN/Infinity.
- Do not truncate. If the requested bank is too large to finish in one response, generate a
  smaller scope (see the caller's `scope`) rather than returning invalid or cut-off JSON.
- Before finishing, silently verify <item_rules> and fill "self_check" honestly; if a
  subtopic in scope could not be fully covered, say so in self_check.notes.
</output_discipline>
"""


def build_prompt(
    scope: Optional[str] = None,
    questions_per_subtopic: Optional[int] = None,
    extra_instructions: Optional[str] = None,
) -> str:
    """Return the generation prompt, optionally appending caller overrides.

    The base prompt is never mutated; overrides are appended in a <caller_overrides>
    block that the model is told takes precedence over <configuration>.
    """
    overrides = []
    if scope:
        overrides.append(f"- scope: {scope}   (generate ONLY this category)")
    if questions_per_subtopic is not None:
        overrides.append(f"- questions_per_subtopic: {questions_per_subtopic}")
    if extra_instructions:
        overrides.append(f"- {extra_instructions}")
    if not overrides:
        return MCQ_GENERATION_PROMPT
    block = (
        "\n\n<caller_overrides>\n"
        "These override the matching values in <configuration>:\n"
        + "\n".join(overrides)
        + "\n</caller_overrides>\n"
    )
    return MCQ_GENERATION_PROMPT + block


# ======================================================================================
# 2) DATA MODEL  (typed, JSON-serialisable, no external deps)
# ======================================================================================
VALID_OPTION_IDS = ("A", "B", "C", "D", "E", "F")

# Order used when sorting a quiz from easiest to hardest. Unknown values sort last.
DIFFICULTY_ORDER = {"easy": 0, "medium": 1, "hard": 2}


@dataclass
class Option:
    id: str
    text: str
    is_correct: bool = False
    distractor_rationale: str = ""


@dataclass
class MCQItem:
    id: str
    stem: str
    options: list[Option]
    correct_option_id: str
    category: str = ""
    subtopic: str = ""
    game_phase: Optional[str] = None
    framing: str = ""
    difficulty: str = ""
    bloom_level: str = ""
    explanation: str = ""
    misconception_tags: list[str] = field(default_factory=list)
    learning_objective: str = ""

    def visible_options(self) -> list[dict]:
        """Options ready for display - WITHOUT revealing which one is correct."""
        return [{"id": o.id, "text": o.text} for o in self.options]

    def is_correct_answer(self, option_id: str) -> bool:
        return option_id.strip().upper() == self.correct_option_id.strip().upper()

    def validate(self) -> list[str]:
        """Return a list of problems (empty == valid)."""
        errors: list[str] = []
        n = len(self.options)
        if not (4 <= n <= 6):
            errors.append(f"{self.id}: has {n} options (must be 4-6)")
        n_correct = sum(1 for o in self.options if o.is_correct)
        if n_correct != 1:
            errors.append(f"{self.id}: {n_correct} options flagged correct (must be exactly 1)")
        flagged = next((o.id for o in self.options if o.is_correct), None)
        if flagged is not None and flagged != self.correct_option_id:
            errors.append(
                f"{self.id}: correct_option_id={self.correct_option_id!r} "
                f"but the flagged option is {flagged!r}"
            )
        ids = [o.id for o in self.options]
        if len(set(ids)) != len(ids):
            errors.append(f"{self.id}: duplicate option ids {ids}")
        bad = [i for i in ids if i not in VALID_OPTION_IDS]
        if bad:
            errors.append(f"{self.id}: invalid option ids {bad} (allowed: A-F)")
        return errors

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class QuestionBank:
    items: list[MCQItem]
    bank_metadata: dict = field(default_factory=dict)
    coverage_manifest: dict = field(default_factory=dict)
    self_check: dict = field(default_factory=dict)

    def __len__(self) -> int:
        return len(self.items)

    def __iter__(self):
        return iter(self.items)

    def validate(self) -> list[str]:
        errors: list[str] = []
        seen: set[str] = set()
        for item in self.items:
            errors.extend(item.validate())
            if item.id in seen:
                errors.append(f"duplicate item id {item.id!r}")
            seen.add(item.id)
        return errors

    def by_difficulty(self, *levels: str) -> "QuestionBank":
        """New bank containing only the given difficulties (e.g. for the 65% gate quiz)."""
        keep = {lvl.lower() for lvl in levels}
        return QuestionBank(
            [i for i in self.items if i.difficulty.lower() in keep],
            self.bank_metadata,
            self.coverage_manifest,
            self.self_check,
        )

    def sorted_by_difficulty(self, reverse: bool = False) -> "QuestionBank":
        """New bank with items ordered easy -> medium -> hard (stable within a tier)."""
        ordered = sorted(
            self.items,
            key=lambda i: DIFFICULTY_ORDER.get(i.difficulty.lower(), 99),
            reverse=reverse,
        )
        return QuestionBank(
            ordered,
            self.bank_metadata,
            self.coverage_manifest,
            self.self_check,
        )


# ======================================================================================
# 3) PARSING  (robust: tolerates code fences / stray prose around the JSON)
# ======================================================================================
def _extract_json(raw: str) -> str:
    """Return the outermost JSON object from a model response.

    Handles the well-behaved case (pure JSON) as well as output accidentally wrapped in
    ```json ... ``` fences or surrounded by a sentence or two of prose.
    """
    s = raw.strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)```", s, re.DOTALL)
    if fenced:
        s = fenced.group(1).strip()
    start, end = s.find("{"), s.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError("No JSON object found in the model output.")
    return s[start : end + 1]


def parse_bank(raw: str, *, strict: bool = True) -> QuestionBank:
    """Parse a model response into a validated QuestionBank.

    strict=True  -> raise ValueError if any item fails validation.
    strict=False -> keep going, stash problems in bank.self_check['_local_validation_errors'].
    """
    data = json.loads(_extract_json(raw))
    items: list[MCQItem] = []
    for d in data.get("items", []):
        options = [
            Option(
                id=str(o["id"]).strip().upper(),
                text=o["text"],
                is_correct=bool(o.get("is_correct", False)),
                distractor_rationale=o.get("distractor_rationale", ""),
            )
            for o in d["options"]
        ]
        items.append(
            MCQItem(
                id=d["id"],
                stem=d["stem"],
                options=options,
                correct_option_id=str(d["correct_option_id"]).strip().upper(),
                category=d.get("category", ""),
                subtopic=d.get("subtopic", ""),
                game_phase=d.get("game_phase"),
                framing=d.get("framing", ""),
                difficulty=d.get("difficulty", ""),
                bloom_level=d.get("bloom_level", ""),
                explanation=d.get("explanation", ""),
                misconception_tags=list(d.get("misconception_tags", [])),
                learning_objective=d.get("learning_objective", ""),
            )
        )
    bank = QuestionBank(
        items=items,
        bank_metadata=data.get("bank_metadata", {}),
        coverage_manifest=data.get("coverage_manifest", {}),
        self_check=data.get("self_check", {}),
    )
    problems = bank.validate()
    if problems:
        if strict:
            raise ValueError("Question bank failed validation:\n  " + "\n  ".join(problems))
        bank.self_check["_local_validation_errors"] = problems
    return bank


# ======================================================================================
# 4) MODEL ADAPTER  (send the prompt string to Gemini; swap for any provider)
# ======================================================================================
# A Generator is any callable that takes the prompt string and returns the model's text.
Generator = Callable[[str], str]


def make_gemini_generator(
    api_key: Optional[str] = None,
    model: str = "gemini-3.1-flash-lite",
    max_output_tokens: int = 8192,
    temperature: float = 0.7,
) -> Generator:
    """Build a generator backed by Google's Gemini API.

    Uses the `google.genai` SDK (the same one as game/ai.py), imported lazily so this
    module stays import-safe without the package installed. If `api_key` is None, the key
    is read from the environment (GEMINI_API_KEY / GOOGLE_API_KEY, e.g. loaded from .env).
    `response_mime_type="application/json"` asks Gemini to return JSON only.
    """

    def _generate(prompt: str) -> str:
        from google.genai import types
        from google import genai
        

        client = genai.Client(api_key=api_key) if api_key else genai.Client()
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                max_output_tokens=max_output_tokens,
                temperature=temperature,
                response_mime_type="application/json",
            ),
        )
        return response.text or ""

    return _generate


def generate_bank(
    generator: Generator,
    *,
    scope: Optional[str] = None,
    questions_per_subtopic: Optional[int] = None,
    extra_instructions: Optional[str] = None,
    strict: bool = True,
) -> QuestionBank:
    """Send the prompt string to the model and parse the result into a QuestionBank."""
    prompt = build_prompt(scope, questions_per_subtopic, extra_instructions)
    raw = generator(prompt)  # <-- the prompt is sent to the AI model here, as a string
    return parse_bank(raw, strict=strict)


# ======================================================================================
# 5) QUIZ  (UI-friendly state machine + a CLI runner that prompts for answers)
# ======================================================================================
@dataclass
class AnswerRecord:
    item_id: str
    chosen_option_id: str
    correct: bool


class Quiz:
    """Drives a question bank one item at a time.

    UI-friendly by design: it performs NO input/output itself. A front end calls
    `current_prompt()` to render a question, then `submit_answer(option_id)` to grade it
    and advance. `results()` gives the final tally (including the 65% gate flag).
    """

    def __init__(self, bank: QuestionBank, shuffle: bool = False,
                 sort_by_difficulty: bool = False):
        self.items: list[MCQItem] = list(bank.items)
        if sort_by_difficulty:
            self.items.sort(key=lambda i: DIFFICULTY_ORDER.get(i.difficulty.lower(), 99))
        if shuffle:
            random.shuffle(self.items)
        self.index: int = 0
        self.answers: list[AnswerRecord] = []

    @property
    def total(self) -> int:
        return len(self.items)

    @property
    def finished(self) -> bool:
        return self.index >= len(self.items)

    @property
    def score(self) -> int:
        return sum(1 for a in self.answers if a.correct)

    def current(self) -> Optional[MCQItem]:
        return None if self.finished else self.items[self.index]

    def current_prompt(self) -> Optional[dict]:
        """Render-ready payload for a UI (no answer key included)."""
        item = self.current()
        if item is None:
            return None
        return {
            "number": self.index + 1,
            "total": self.total,
            "id": item.id,
            "stem": item.stem,
            "options": item.visible_options(),
            "category": item.category,
            "difficulty": item.difficulty,
        }

    def submit_answer(self, option_id: str) -> dict:
        """Grade the current question, record it, and advance. Returns feedback."""
        item = self.current()
        if item is None:
            raise RuntimeError("Quiz is already finished.")
        correct = item.is_correct_answer(option_id)
        self.answers.append(AnswerRecord(item.id, option_id.strip().upper(), correct))
        self.index += 1
        return {
            "correct": correct,
            "correct_option_id": item.correct_option_id,
            "explanation": item.explanation,
        }

    def results(self, gate_percent: float = 65.0) -> dict:
        """Final tally as pure data (no printing, so a UI can consume it too)."""
        pct = round(100 * self.score / self.total, 1) if self.total else 0.0
        return {
            "score": self.score,
            "total": self.total,
            "percent": pct,
            "gate_percent": gate_percent,
            "passed_gate": pct >= gate_percent,
            "answers": [asdict(a) for a in self.answers],
        }


def verdict_message(percent: float, gate_percent: float = 65.0) -> str:
    """A flavor line based on the PLAYER'S score (not the gate)."""
    if percent <= 0:
        return "YOU'RE FIRED"
    if percent < 20:
        return "BAD THINGS ARE COMING YOUR WAY UNLESS YOU PRACTICE MORE"
    if percent < 40:
        return "IT'S NOT LOOKING GOOD FOR YOU"
    if percent < gate_percent:
        return "THIS IS NOT OKAY"
    return "PAYDAY COMING YOUR WAY!!!!"


def run_cli_quiz(bank: QuestionBank, gate_percent: float = 65.0) -> dict:
    """Interactive terminal quiz: PROMPTS THE USER for each answer and shows feedback.

    Questions are presented easy -> medium -> hard.
    """
    quiz = Quiz(bank, sort_by_difficulty=True)
    print(f"\n=== PENN GOATS money quiz - {quiz.total} questions ===\n")
    while not quiz.finished:
        p = quiz.current_prompt()
        assert p is not None
        tag = " / ".join(x for x in (p["category"], p["difficulty"]) if x)
        header = f"Q{p['number']}/{p['total']}"
        print(f"{header}  [{tag}]" if tag else header)
        print(p["stem"])
        for opt in p["options"]:
            print(f"  {opt['id']}) {opt['text']}")
        valid = [opt["id"].upper() for opt in p["options"]]   # this question's real 4-6 letters
        while True:
            choice = input(f"Your answer ({'/'.join(valid)}): ").strip().upper()
            if choice in valid:
                break
            print(f"  Please enter one of: {', '.join(valid)}")
        feedback = quiz.submit_answer(choice)
        if feedback["correct"]:
            print("  [correct]")
        else:
            print(f"  [incorrect] - correct answer is {feedback['correct_option_id']}")
        if feedback["explanation"]:
            print(f"  -> {feedback['explanation']}")
        print()

    res = quiz.results(gate_percent)
    print("=" * 50)
    print(f"Final score: {res['score']}/{res['total']} ({res['percent']}%)")
    print(verdict_message(res["percent"], gate_percent))
    print("=" * 50)
    return res





    
