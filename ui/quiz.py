"""Builds the money quiz for the UI, with async prefetching.

One topic per in-game day, a random 8-10 questions easy -> hard. To avoid stalls, the day's
bank is generated on a background thread during play (prefetch) and cached; if it isn't
ready the quiz falls back instantly to a built-in bank. Options are pre-shuffled by
parse_bank, so the correct answer is never stuck at "B".
"""

import os
import random
import threading

from game.mcq import (
    make_gemini_generator, generate_bank, parse_bank, QuestionBank,
    topic_for_day, DIFFICULTY_ORDER,
)

# Subtopics per category -> used to size each generation so the pool is comfortably >= 10.
# Small categories get more per subtopic.
SUBTOPIC_COUNTS = {
    "INCOME": 6, "INVESTING": 10, "TAXES": 3, "DEBT & CREDIT": 6,
    "BUDGETING & CASH FLOW": 4, "NET WORTH & GOALS": 3,
    "WELLBEING & BEHAVIOR": 3, "RISK & LIFE EVENTS": 3,
}

MIN_QUESTIONS, MAX_QUESTIONS = 8, 10


def _qps_for(topic: str) -> int:
    """Questions per subtopic, chosen so the generated pool is >= ~10 without ballooning
    big categories into a truncation risk."""
    return 3 if SUBTOPIC_COUNTS.get(topic, 6) <= 5 else 2


# --- built-in fallback bank (used with no API key, or before a prefetch finishes) -------
_FALLBACK_JSON = """
{
  "bank_metadata": {"audience": "US young adults", "currency": "USD", "generated_for": "fallback"},
  "items": [
    {"id":"INC-gross-vs-net-001","category":"INCOME","subtopic":"gross-vs-net","difficulty":"easy","framing":"concept",
     "stem":"Your offer says $4,000 a month. Which figure is your take-home pay?",
     "options":[{"id":"A","text":"The full $4,000 — that's your salary.","is_correct":false,"distractor_rationale":"Ignores withholdings."},
       {"id":"B","text":"$4,000 minus taxes and other withholdings.","is_correct":true,"distractor_rationale":"correct answer"},
       {"id":"C","text":"$4,000 plus any overtime, before tax.","is_correct":false,"distractor_rationale":"Describes gross."},
       {"id":"D","text":"Only the part withheld for Social Security and Medicare.","is_correct":false,"distractor_rationale":"Confuses net with FICA."}],
     "correct_option_id":"B","explanation":"Take-home (net) pay is your gross offer minus federal, state, and FICA withholdings."},
    {"id":"INC-withholdings-001","category":"INCOME","subtopic":"withholdings","difficulty":"easy","framing":"concept",
     "stem":"Which of these is a FICA payroll tax?",
     "options":[{"id":"A","text":"Social Security and Medicare tax.","is_correct":true,"distractor_rationale":"correct answer"},
       {"id":"B","text":"Sales tax on things you buy.","is_correct":false,"distractor_rationale":"Sales tax is unrelated to payroll."},
       {"id":"C","text":"Property tax on a home.","is_correct":false,"distractor_rationale":"Property tax isn't withheld from pay."},
       {"id":"D","text":"A late fee on a credit card.","is_correct":false,"distractor_rationale":"Not a tax at all."}],
     "correct_option_id":"A","explanation":"FICA funds Social Security and Medicare and is withheld from every paycheck."},
    {"id":"BUD-liquidity-001","category":"BUDGETING & CASH FLOW","subtopic":"liquidity-emergency","difficulty":"easy","framing":"concept",
     "stem":"What is the main point of an emergency fund?",
     "options":[{"id":"A","text":"Accessible cash to cover a surprise cost without borrowing.","is_correct":true,"distractor_rationale":"correct answer"},
       {"id":"B","text":"A high-return investment for long-term growth.","is_correct":false,"distractor_rationale":"Confuses a buffer with an investment."},
       {"id":"C","text":"Money you must spend by year-end.","is_correct":false,"distractor_rationale":"Invents a use-it-or-lose-it rule."},
       {"id":"D","text":"A type of loan from your bank.","is_correct":false,"distractor_rationale":"It's your own cash, not debt."}],
     "correct_option_id":"A","explanation":"An emergency fund is liquid cash set aside so a shock doesn't force you into debt."},
    {"id":"NW-net-worth-formula-001","category":"NET WORTH & GOALS","subtopic":"net-worth-formula","difficulty":"easy","framing":"concept",
     "stem":"How is net worth calculated in the game?",
     "options":[{"id":"A","text":"Cash plus investments, minus liabilities.","is_correct":true,"distractor_rationale":"correct answer"},
       {"id":"B","text":"Just the cash in your account.","is_correct":false,"distractor_rationale":"Ignores investments and debt."},
       {"id":"C","text":"Your monthly take-home pay.","is_correct":false,"distractor_rationale":"That's income, not net worth."},
       {"id":"D","text":"Investments minus cash.","is_correct":false,"distractor_rationale":"Wrong combination."}],
     "correct_option_id":"A","explanation":"Net worth = (cash + investments) - liabilities."},
    {"id":"INV-risk-return-001","category":"INVESTING","subtopic":"risk-return","difficulty":"medium","framing":"concept",
     "stem":"In general, an investment with a higher expected return also tends to have:",
     "options":[{"id":"A","text":"Higher risk (bigger ups and downs).","is_correct":true,"distractor_rationale":"correct answer"},
       {"id":"B","text":"Lower risk than a savings account.","is_correct":false,"distractor_rationale":"Reverses the trade-off."},
       {"id":"C","text":"No risk at all.","is_correct":false,"distractor_rationale":"No high-return asset is risk-free."},
       {"id":"D","text":"A guaranteed monthly payout.","is_correct":false,"distractor_rationale":"Confuses returns with a guarantee."}],
     "correct_option_id":"A","explanation":"Risk and expected return move together — higher returns mean more volatility."},
    {"id":"INV-compounding-001","category":"INVESTING","subtopic":"compounding","difficulty":"medium","framing":"concept",
     "stem":"Why does starting to invest earlier matter so much?",
     "options":[{"id":"A","text":"Returns compound — gains earn their own gains over time.","is_correct":true,"distractor_rationale":"correct answer"},
       {"id":"B","text":"Older investors pay no taxes.","is_correct":false,"distractor_rationale":"Age doesn't remove taxes."},
       {"id":"C","text":"Early money is immune to market drops.","is_correct":false,"distractor_rationale":"No money is immune to volatility."},
       {"id":"D","text":"Banks pay a bonus for opening young.","is_correct":false,"distractor_rationale":"Invents a bonus."}],
     "correct_option_id":"A","explanation":"Compounding means each period's growth is added to the base, so time is your biggest ally."},
    {"id":"DEBT-credit-cards-001","category":"DEBT & CREDIT","subtopic":"credit-cards","difficulty":"medium","framing":"concept",
     "stem":"Why is credit-card debt usually the most dangerous kind to carry?",
     "options":[{"id":"A","text":"It typically has the highest interest rate, so balances grow fast.","is_correct":true,"distractor_rationale":"correct answer"},
       {"id":"B","text":"It is the only debt with any interest.","is_correct":false,"distractor_rationale":"All these debts charge interest."},
       {"id":"C","text":"It must be paid off in a single lump sum.","is_correct":false,"distractor_rationale":"Cards revolve."},
       {"id":"D","text":"It never appears on your statement.","is_correct":false,"distractor_rationale":"Factually wrong."}],
     "correct_option_id":"A","explanation":"Cards carry the highest rates; paying only the minimum lets interest snowball."},
    {"id":"BUD-needs-wants-001","category":"BUDGETING & CASH FLOW","subtopic":"needs-vs-wants","difficulty":"medium","framing":"scenario",
     "stem":"Rent, groceries, and a concert ticket. Which is discretionary (a want)?",
     "options":[{"id":"A","text":"The concert ticket.","is_correct":true,"distractor_rationale":"correct answer"},
       {"id":"B","text":"The rent.","is_correct":false,"distractor_rationale":"Housing is a need."},
       {"id":"C","text":"The groceries.","is_correct":false,"distractor_rationale":"Food is a need."},
       {"id":"D","text":"All three are needs.","is_correct":false,"distractor_rationale":"A concert is optional."}],
     "correct_option_id":"A","explanation":"Needs are mandatory (housing, food); wants are optional spending like entertainment."},
    {"id":"TAX-capital-gains-001","category":"TAXES","subtopic":"capital-gains","difficulty":"hard","framing":"scenario",
     "stem":"You sell an index-fund position for $3,000 that you bought for $2,000. Capital-gains tax is 15% on the profit only. How much tax is added?",
     "options":[{"id":"A","text":"$150","is_correct":true,"distractor_rationale":"correct answer"},
       {"id":"B","text":"$300","is_correct":false,"distractor_rationale":"Taxes the $2,000 basis."},
       {"id":"C","text":"$450","is_correct":false,"distractor_rationale":"Taxes the full $3,000 of proceeds."},
       {"id":"D","text":"$20","is_correct":false,"distractor_rationale":"Applies roughly a 1% rate."},
       {"id":"E","text":"$0 — selling just moves value into cash.","is_correct":false,"distractor_rationale":"Selling realizes a taxable gain."}],
     "correct_option_id":"A","explanation":"Profit is $3,000 - $2,000 = $1,000; 15% of $1,000 = $150."},
    {"id":"DEBT-minimum-payments-001","category":"DEBT & CREDIT","subtopic":"minimum-payments","difficulty":"hard","framing":"concept",
     "stem":"If you only ever pay the minimum on a high-interest card, what usually happens?",
     "options":[{"id":"A","text":"The balance shrinks very slowly as interest keeps piling on.","is_correct":true,"distractor_rationale":"correct answer"},
       {"id":"B","text":"The debt is cleared within a couple of months.","is_correct":false,"distractor_rationale":"Minimums barely dent principal."},
       {"id":"C","text":"Interest stops being charged.","is_correct":false,"distractor_rationale":"Interest keeps accruing."},
       {"id":"D","text":"The card issuer forgives the rest.","is_correct":false,"distractor_rationale":"No forgiveness for paying the minimum."}],
     "correct_option_id":"A","explanation":"Minimum payments mostly cover interest, so principal falls slowly and the debt lingers for years."}
  ],
  "coverage_manifest": {},
  "self_check": {}
}
"""

# --- async cache: topic -> QuestionBank (or None if the generation failed) --------------
_LOCK = threading.Lock()
_BANKS: dict = {}          # ready results, keyed by topic
_INFLIGHT: set = set()     # topics currently generating


def _prime(topic: str, generator=None) -> None:
    """Generate a topic's bank and store it in the cache. Runs on a background thread in
    production; called directly in tests. Never raises.

    Parses with strict=False and drops only the individual items that fail validation, so
    one malformed question can't discard an otherwise-good bank (which would waste the
    generation and fall back to the generic bank). The bank is stored only if at least one
    valid item survives; otherwise None -> callers fall back."""
    bank = None
    try:
        gen = generator
        if gen is None and os.getenv("GEMINI_API_KEY"):
            gen = make_gemini_generator()
        if gen is not None:
            raw = generate_bank(gen, scope=topic,
                                questions_per_subtopic=_qps_for(topic), strict=False)
            good = [it for it in raw.items if not it.validate()]
            if good:
                bank = QuestionBank(good, raw.bank_metadata, {}, raw.self_check)
    except Exception:
        bank = None
    with _LOCK:
        _BANKS[topic] = bank            # may be None -> callers fall back
        _INFLIGHT.discard(topic)


def prefetch(day: int, generator=None) -> str:
    """Kick off async generation for the given day's topic. Idempotent and non-blocking:
    a no-op if that topic is already cached or in flight. Returns the topic."""
    topic = topic_for_day(day)
    with _LOCK:
        if topic in _BANKS or topic in _INFLIGHT:
            return topic
        _INFLIGHT.add(topic)
    threading.Thread(target=_prime, args=(topic, generator), daemon=True).start()
    return topic


def is_ready(day: int) -> bool:
    with _LOCK:
        return _BANKS.get(topic_for_day(day)) is not None


def clear_cache() -> None:
    with _LOCK:
        _BANKS.clear()
        _INFLIGHT.clear()


def _sample(bank: QuestionBank, n: int, rng: random.Random) -> QuestionBank:
    items = list(bank.items)
    rng.shuffle(items)
    items = items[:n]
    items.sort(key=lambda i: DIFFICULTY_ORDER.get(i.difficulty.lower(), 99))   # easy -> hard
    return QuestionBank(items, bank.bank_metadata, {}, bank.self_check)


def build_daily_quiz(day: int, n=None, generator=None, seed: int = 0):
    """Return (topic, QuestionBank, used_ai) for the day. Uses the prefetched bank if it's
    ready; otherwise falls back to the built-in bank immediately (never stalls the UI).
    `n` defaults to a random 8-10; pass an int to pin it (tests)."""
    topic = topic_for_day(day)
    rng = random.Random(seed)
    if n is None:
        n = rng.randint(MIN_QUESTIONS, MAX_QUESTIONS)

    with _LOCK:
        bank = _BANKS.get(topic)               # None if missing OR a failed generation
        seen = topic in _BANKS
    if not seen:
        prefetch(day, generator)               # warm it for next time; use fallback now

    used_ai = bank is not None
    if bank is None:
        bank = parse_bank(_FALLBACK_JSON)       # options shuffled by default
    return topic, _sample(bank, n, rng), used_ai
