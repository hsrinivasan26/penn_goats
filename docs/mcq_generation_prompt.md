# MCQ Generation Prompt — PENN GOATS

A reusable prompt that makes Claude emit a **machine-parsable bank of multiple-choice
questions** covering every financial concept in the game's logic tree. Output is a single
JSON object (no prose), so it drops straight into a database or quiz engine.

**How to use**

- Copy everything between the `PROMPT START` / `PROMPT END` markers and send it to Claude
  (paste into the app, or use it as the user message via the API).
- Edit the `<configuration>` block to change counts, framing mix, or difficulty.
- For a large bank, generate **one category at a time** (set `scope` to a single category)
  so responses stay complete and valid — see *Run notes* at the bottom.

---

## ===== PROMPT START =====

<role>
You are a financial-literacy assessment designer and professional item writer. You create
rigorous, unambiguous multiple-choice questions (MCQs) for a personal-finance simulation
game aimed at young adults (ages ~17–29) in the United States. Each question both teaches
and assesses a real financial concept, using either a plain-concept framing or an in-game
scenario framing. Make it python and UI friendly
</role>

<configuration>
Use these settings (defaults shown; the caller may override them):
- questions_per_subtopic: 3        # produce 1 easy + 1 medium + 1 hard for each subtopic
- framing_mix: ~50% concept, ~50% scenario (across the whole bank)
- audience: United States young adults; reading level grade 8–10
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

A. INCOME — code INC  [Phase 1: Income]
   - getting-hired: pay scales with a job's difficulty/skill and your education + experience
   - gross-vs-net: gross pay vs. net (take-home) pay
   - withholdings: Federal income tax, State income tax, and FICA (Social Security + Medicare)
   - paystub-literacy: reading a paystub and its deductions
   - career-growth: education/experience unlock higher-paying jobs and raises over time
   - income-risk: losing income to layoffs or a company going bankrupt

B. INVESTING — code INV  [Phase 2: Markets]
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

C. TAXES — code TAX  [Phase 5: Events]
   - progressive-brackets: progressive income tax; marginal vs. effective rate
   - capital-gains: tax charged on the PROFIT when investments are sold
   - annual-reconciliation: yearly tax bill vs. what was already withheld from paychecks

D. DEBT & CREDIT — code DEBT  [Phase 3: Interest & liabilities / Phase 4: Outflows]
   - student-loans: interest accrual; repayment (with interest) begins after graduation
   - college-choice: public vs. private university — cost vs. potential reward
   - mortgage-vs-rent: buy with a mortgage (monthly payment) vs. pay flat-rate rent
   - credit-cards: highest interest rate; minimum payments; revolving-debt spiral
   - interest-mechanics: how interest makes balances grow; principal vs. interest
   - minimum-payments: required monthly debt outflows and what happens if you miss them

E. BUDGETING & CASH FLOW — code BUD  [Phase 4: Forced outflows]
   - essentials: required outflows (housing, food, transport, utilities)
   - needs-vs-wants: distinguishing mandatory bills from discretionary spending
   - shortfall: spending more than available cash pushes the gap into debt (shortfall flag)
   - liquidity-emergency: keeping accessible cash / an emergency fund

F. NET WORTH & GOALS — code NW  [Phase 8: Win check]
   - net-worth-formula: Net Worth = (cash + investments) − liabilities
   - bankruptcy: losing when net worth falls to 0 or below
   - goal-target: saving toward a target net worth by the final turn

G. WELLBEING & BEHAVIOR — code WELL  [Phase 7: Happiness]
   - leisure-happiness: discretionary/leisure spending raises happiness
   - burnout: happiness decays; hitting 0 ends the game; work-life balance
   - lifestyle-inflation: spending rising with income; the save-vs-spend trade-off

H. RISK & LIFE EVENTS — code RISK  [Phase 5: Events]
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
  "each_item_has_exactly_one_correct_option", "all_items_have_four_options", and a
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
- "options": array of EXACTLY 4 objects, each:
    { "id": "A"|"B"|"C"|"D", "text": string, "is_correct": boolean,
      "distractor_rationale": string }   // for the correct option, use "correct answer"
- "correct_option_id": string, "A" | "B" | "C" | "D" (exactly one item is_correct=true).
- "explanation": string, 1–3 sentences teaching why the answer is right.
- "misconception_tags": array of short strings naming the misconception each distractor targets.
- "learning_objective": string, one sentence.
</output_format>

<item_rules>
1. Exactly 4 options (A–D); exactly ONE is correct.
2. Exactly one defensibly-best answer. Every distractor must be plausible and target a
   SPECIFIC named misconception (state it in distractor_rationale and misconception_tags).
3. No "All of the above" / "None of the above". Avoid negative stems ("which is NOT")
   unless the NOT is capitalized and the item truly needs it.
4. Keep options parallel in length and grammar; do not make the correct answer the longest.
5. Vary the position of the correct answer across items (do not default to B).
6. Items are self-contained: include any numbers needed in the stem; never reference
   another question.
7. Use realistic but FICTIONAL figures. For stocks/crypto/funds use generic or invented
   names ("a crypto token", "a broad index fund", "Fund X") — never real tickers, and
   never give buy/sell or personalized financial advice. Assess knowledge, not decisions.
8. US context. Spell out an acronym on first use in a stem when it aids clarity
   (e.g., "FICA (Social Security and Medicare tax)").
9. Difficulty calibration:
   - easy   = recall/definition (recall/understand).
   - medium = single-step application (apply).
   - hard   = multi-step reasoning or a trade-off/comparison (apply/analyze), e.g. compute
     net pay from gross, distinguish marginal vs. effective rate, compare rent vs. mortgage.
10. framing="scenario" items use the game world — a character with a job; the four sliders
    (cash, investments, liabilities, happiness); a turn = one month; annual tax at year-end
    — but must remain solvable from the stem alone.
11. explanation should teach the concept and briefly note why the key distractors are wrong.
12. Honor questions_per_subtopic and the difficulty spread for every in-scope subtopic.
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
    { "id": "B", "text": "$300", "is_correct": false, "distractor_rationale": "Taxes the $2,000 cost basis instead of the gain." },
    { "id": "C", "text": "$450", "is_correct": false, "distractor_rationale": "Taxes the full $3,000 of proceeds, not the profit." },
    { "id": "D", "text": "$0, because selling just moves value into cash.", "is_correct": false, "distractor_rationale": "Assumes selling is untaxed; selling realizes a taxable gain." }
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

## ===== PROMPT END =====

---

## Run notes

**Chat (Claude app).** Paste the prompt block. If a bank gets cut off, don't stitch a
partial JSON together — instead set `scope` in `<configuration>` to a single category
(e.g. `scope: TAXES`) and run once per category; concatenate the `items` arrays yourself.

**API (recommended for guaranteed-parseable output).** Send the prompt block as the user
message and enforce the shape with **structured outputs / tool use**: define a JSON Schema
matching `<output_format>` and pass it as the response format (or as a single tool the model
must call). That makes the model's output conform to the schema so you can parse it without
defensive cleanup. Generate per-category to avoid truncation; `temperature` ~0.7 gives
variety, lower (~0.3) gives more consistent phrasing.

**Validation before you store items.** Reject any item where the number of options ≠ 4, or
where the count of `is_correct: true` ≠ 1, or where `correct_option_id` doesn't match the
option flagged correct. Spot-check that `coverage_manifest` lists every in-scope subtopic.

**Tuning knobs (in `<configuration>`).** `questions_per_subtopic` for bank size;
`framing_mix` to weight concept vs. scenario; `scope` to shard by category. To feed the
game's 65%-accuracy gate for private university, draw the gate quiz from `difficulty: medium`
and `hard` items so it actually discriminates.

**De-duplication across runs.** Item ids are only unique within a run. When merging banks,
re-namespace ids (e.g., prefix a batch number) and check for near-duplicate stems.

---

## AI biases & limitations

These questions are LLM-generated, so they inherit biases from the model's training data
and from the way LLMs write test items. Because a skewed or wrong question misteaches a
concept — and because this quiz **gates progression** (the 65% private-university gate) — a
biased item can unfairly help or block a player. Treat every generated bank as a **draft that
a human reviews before it reaches players.** Below are the failure modes to watch for, how
each tends to show up in our questions, and how we reduce it.

1. **US-centric / cultural bias.** The model assumes a US framing (FICA, federal/state
   brackets, US college and mortgage norms). That fits our US young-adult audience, but the
   rules and numbers are US-specific and shouldn't be treated as universal. *Mitigation:*
   audience and currency are pinned in `<configuration>`; don't reuse a bank for non-US
   contexts without review.

2. **Socioeconomic / "normative path" bias.** LLMs lean toward a middle-class default —
   everyone goes to college, lands a salaried job, buys a home, invests spare cash. This can
   misrepresent first-gen, low-income, or non-traditional players, and can bake class
   assumptions into "wants vs. needs." *Mitigation:* review scenarios for assumed disposable
   income/assets; include paths without college or homeownership; keep essentials realistic.

3. **Financial-opinion-as-fact bias.** The model presents mainstream advice as objectively
   correct ("index funds are best," "debt is bad," "always buy over rent"), even where the
   topic is genuinely contested. If a contested opinion becomes the keyed answer, we teach a
   value as a fact. *Mitigation:* for debatable topics (rent vs. buy, active vs. passive,
   crypto), key the answer on the *mechanism or trade-off* ("renting avoids maintenance costs
   and illiquidity"), not a verdict; flag opinionated items in review.

4. **Representation & stereotyping bias (scenario framing).** Names, jobs, genders, and
   spending in scenario questions can skew — Anglocentric names, gendered occupations
   (women shopping, men investing), or stereotyped associations. *Mitigation:* vary names and
   demographics; never tie competence or spending habits to gender/ethnicity; scan the
   scenario set for a stereotyped pattern.

5. **Factual & math errors (hallucination).** Computed items (net pay, capital-gains,
   interest, marginal vs. effective rate) are where the keyed answer is most often wrong, and
   dollar figures for salaries/rent/prices may be outdated. A wrong "correct answer" actively
   misteaches. *Mitigation:* independently recompute every numeric item; sanity-check dollar
   amounts against today's reality; treat `hard` computed items as the top review priority.

6. **Item-writing / psychometric bias.** LLMs leave tells a test-savvy student can exploit:
   the correct option is often the longest or most-qualified, or sits in a habitual position
   (frequently "B"); distractors with absolute words ("always/never") are predictably wrong;
   distractors are sometimes implausible (too easy) or, worse, arguably also correct
   (ambiguous). *Mitigation:* the prompt already tells the model to vary answer position and
   match option length/grammar (rules #4–5), but verify — check the spread of correct letters
   across a bank and confirm no distractor is defensible.

7. **Difficulty miscalibration.** The model's easy/medium/hard labels may not match our
   audience, and difficulty can cluster or be mislabeled — which matters because the gate
   draws on difficulty. *Mitigation:* sample a few items per tier and confirm the labels fit a
   grade 8–10 reader; adjust the gate's item pool if a tier is off.

8. **Reading-level / accessibility bias.** Despite the grade 8–10 instruction, the model may
   slip into jargon or long sentences, disadvantaging readers regardless of their financial
   knowledge. *Mitigation:* skim for undefined jargon and sentence length — the goal is to
   test the concept, not reading stamina.

9. **Homogeneity / low diversity.** Across a large bank the model reuses stems, scenarios,
   and phrasing, so coverage looks broad but variety is thin. *Mitigation:* de-duplicate
   near-identical stems (see Run notes); generate per-category and vary prompts if needed.

10. **Feedback-loop / fairness risk.** Because the quiz gates progression, any bias above can
    unfairly block a player (e.g., someone tripped up by a US-centric or ambiguous item is
    denied the private-university path). *Mitigation:* keep the gate pool reviewed and
    unambiguous; consider allowing retries; watch which items are missed most.

11. **Automation bias (ours, not the model's).** The biggest risk is trusting the output
    because it's fast and well-formatted. *Mitigation:* every bank is a draft until a human
    signs off.

### Quick review checklist (per generated bank)

- [ ] Recomputed every numeric answer; the keyed option is correct.
- [ ] No keyed answer states a contested opinion as fact.
- [ ] Correct-answer letters are spread out; the correct option isn't consistently the longest.
- [ ] Every distractor is plausible and clearly wrong (no second defensible answer).
- [ ] Scenario names / jobs / demographics are varied and non-stereotyped.
- [ ] Difficulty labels feel right; the gate pool (medium/hard) is clean.
- [ ] Reading level ~grade 8–10; no undefined jargon.
- [ ] No near-duplicate stems.
