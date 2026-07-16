"""Builds the daily work quiz for the UI.

One topic per in-game day (rotating via game.mcq.topic_for_day), a handful of questions
easy -> hard. Generates with Gemini when GEMINI_API_KEY is set; otherwise falls back to a
small built-in bank so the screen still works offline / without a key. Option positions are
already shuffled by parse_bank, so the correct answer is never stuck at "B".
"""

import os
import random

from game.mcq import (
    make_gemini_generator, generate_bank, parse_bank, QuestionBank,
    topic_for_day, DIFFICULTY_ORDER,
)

# A small, hand-written bank used when Gemini isn't available. Valid per the schema
# (one item has 5 options to satisfy the "not all 4-choice" rule).
_FALLBACK_JSON = """
{
  "bank_metadata": {"audience": "US young adults", "currency": "USD", "generated_for": "fallback"},
  "items": [
    {"id": "INC-gross-vs-net-001", "category": "INCOME", "subtopic": "gross-vs-net",
     "difficulty": "easy", "framing": "concept",
     "stem": "Your offer says $4,000 a month. Which figure is your take-home pay?",
     "options": [
       {"id":"A","text":"The full $4,000 — that's your salary.","is_correct":false,"distractor_rationale":"Ignores withholdings."},
       {"id":"B","text":"$4,000 minus taxes and other withholdings.","is_correct":true,"distractor_rationale":"correct answer"},
       {"id":"C","text":"$4,000 plus any overtime, before tax.","is_correct":false,"distractor_rationale":"Describes gross, not net."},
       {"id":"D","text":"Only the part withheld for Social Security and Medicare.","is_correct":false,"distractor_rationale":"Confuses net pay with the FICA deduction."}],
     "correct_option_id": "B",
     "explanation": "Take-home (net) pay is your gross offer minus federal, state, and FICA withholdings."},
    {"id": "BUD-liquidity-001", "category": "BUDGETING & CASH FLOW", "subtopic": "liquidity-emergency",
     "difficulty": "easy", "framing": "concept",
     "stem": "What is the main point of an emergency fund?",
     "options": [
       {"id":"A","text":"Accessible cash to cover a surprise cost without borrowing.","is_correct":true,"distractor_rationale":"correct answer"},
       {"id":"B","text":"A high-return investment for long-term growth.","is_correct":false,"distractor_rationale":"Confuses a buffer with an investment."},
       {"id":"C","text":"Money you must spend by year-end.","is_correct":false,"distractor_rationale":"Invents a use-it-or-lose-it rule."},
       {"id":"D","text":"A type of loan from your bank.","is_correct":false,"distractor_rationale":"An emergency fund is your own cash, not debt."}],
     "correct_option_id": "A",
     "explanation": "An emergency fund is liquid cash set aside so a shock doesn't force you into debt."},
    {"id": "INV-risk-return-001", "category": "INVESTING", "subtopic": "risk-return",
     "difficulty": "medium", "framing": "concept",
     "stem": "In general, an investment with a higher expected return also tends to have:",
     "options": [
       {"id":"A","text":"Higher risk (bigger ups and downs).","is_correct":true,"distractor_rationale":"correct answer"},
       {"id":"B","text":"Lower risk than a savings account.","is_correct":false,"distractor_rationale":"Reverses the risk-return trade-off."},
       {"id":"C","text":"No risk at all.","is_correct":false,"distractor_rationale":"No real asset is risk-free with high returns."},
       {"id":"D","text":"A guaranteed payout each month.","is_correct":false,"distractor_rationale":"Confuses returns with a fixed income guarantee."}],
     "correct_option_id": "A",
     "explanation": "Risk and expected return move together — chasing higher returns means accepting more volatility."},
    {"id": "DEBT-credit-cards-001", "category": "DEBT & CREDIT", "subtopic": "credit-cards",
     "difficulty": "medium", "framing": "concept",
     "stem": "Why is credit-card debt usually the most dangerous kind to carry?",
     "options": [
       {"id":"A","text":"It typically has the highest interest rate, so balances grow fast.","is_correct":true,"distractor_rationale":"correct answer"},
       {"id":"B","text":"It is the only debt with any interest.","is_correct":false,"distractor_rationale":"All these debts charge interest."},
       {"id":"C","text":"It must be paid off in a single lump sum.","is_correct":false,"distractor_rationale":"Cards allow revolving balances."},
       {"id":"D","text":"It never appears on your statement.","is_correct":false,"distractor_rationale":"Factually wrong."}],
     "correct_option_id": "A",
     "explanation": "Credit cards carry the highest rates; paying only the minimum lets interest snowball."},
    {"id": "TAX-capital-gains-001", "category": "TAXES", "subtopic": "capital-gains",
     "difficulty": "hard", "framing": "scenario",
     "stem": "You sell an index-fund position for $3,000 that you bought for $2,000. Capital-gains tax is 15% on the profit only. How much tax is added?",
     "options": [
       {"id":"A","text":"$150","is_correct":true,"distractor_rationale":"correct answer"},
       {"id":"B","text":"$300","is_correct":false,"distractor_rationale":"Taxes the $2,000 basis instead of the gain."},
       {"id":"C","text":"$450","is_correct":false,"distractor_rationale":"Taxes the full $3,000 of proceeds."},
       {"id":"D","text":"$20","is_correct":false,"distractor_rationale":"Applies roughly a 1% rate, not 15%."},
       {"id":"E","text":"$0 — selling just moves value into cash.","is_correct":false,"distractor_rationale":"Selling realizes a taxable gain."}],
     "correct_option_id": "A",
     "explanation": "Profit is $3,000 - $2,000 = $1,000; 15% of $1,000 = $150."},
    {"id": "NW-net-worth-formula-001", "category": "NET WORTH & GOALS", "subtopic": "net-worth-formula",
     "difficulty": "easy", "framing": "concept",
     "stem": "How is net worth calculated in the game?",
     "options": [
       {"id":"A","text":"Cash plus investments, minus liabilities.","is_correct":true,"distractor_rationale":"correct answer"},
       {"id":"B","text":"Just the cash in your account.","is_correct":false,"distractor_rationale":"Ignores investments and debt."},
       {"id":"C","text":"Your monthly take-home pay.","is_correct":false,"distractor_rationale":"That's income, not net worth."},
       {"id":"D","text":"Investments minus cash.","is_correct":false,"distractor_rationale":"Wrong combination of terms."}],
     "correct_option_id": "A",
     "explanation": "Net worth = (cash + investments) - liabilities. Debt subtracts; assets add."}
  ],
  "coverage_manifest": {},
  "self_check": {}
}
"""


def _sample(bank: QuestionBank, n: int, rng: random.Random) -> QuestionBank:
    """Pick up to n items, then order them easy -> hard for a gentle ramp."""
    items = list(bank.items)
    rng.shuffle(items)
    items = items[:n]
    items.sort(key=lambda i: DIFFICULTY_ORDER.get(i.difficulty.lower(), 99))
    return QuestionBank(items, bank.bank_metadata, {}, bank.self_check)


def build_daily_quiz(day: int, n: int = 5, generator=None, seed: int = 0):
    """Return (topic, QuestionBank, used_ai) for the given in-game day.

    Tries Gemini for the day's single topic; on any failure (no key, network, bad output)
    it falls back to the built-in bank so the screen never hard-fails.
    """
    topic = topic_for_day(day)
    rng = random.Random(seed)
    gen = generator
    if gen is None and os.getenv("GEMINI_API_KEY"):
        try:
            gen = make_gemini_generator()
        except Exception:
            gen = None
    bank = None
    if gen is not None:
        try:
            bank = generate_bank(gen, scope=topic, questions_per_subtopic=1)
        except Exception:
            bank = None
    used_ai = bank is not None
    if bank is None:
        bank = parse_bank(_FALLBACK_JSON)          # options shuffled by default
    return topic, _sample(bank, n, rng), used_ai
