"""Tests for the MCQ engine after the bias-hardening pass.

Covers: option shuffling (the "always B" fix), 4-6 option validation, quiz scoring
and the 65% gate, difficulty tiers, and per-day topic rotation. No live model calls --
everything runs off a fixed sample bank.
"""

import json
import random

import pytest

from game.mcq import (
    parse_bank, shuffle_item_options, Quiz, verdict_message, build_prompt,
    topic_for_day, CATEGORY_NAMES, DIFFICULTY_LABELS, VALID_OPTION_IDS,
)

# A small but valid bank: correct answers start at B / A / D, and item 2 has 5 options
# (so the "at least one 5-6-option question" rule is satisfied).
SAMPLE = """
{
  "bank_metadata": {"audience": "US young adults", "currency": "USD", "total_items": 3},
  "items": [
    {"id": "INC-gross-vs-net-001", "category": "INCOME", "subtopic": "gross-vs-net",
     "difficulty": "easy", "framing": "concept", "stem": "What is net pay?",
     "options": [
       {"id": "A", "text": "The full gross salary", "is_correct": false, "distractor_rationale": "d"},
       {"id": "B", "text": "Take-home after withholdings", "is_correct": true, "distractor_rationale": "correct answer"},
       {"id": "C", "text": "Salary plus bonus", "is_correct": false, "distractor_rationale": "d"},
       {"id": "D", "text": "FICA only", "is_correct": false, "distractor_rationale": "d"}],
     "correct_option_id": "B", "explanation": "Net is gross minus withholdings."},
    {"id": "INV-risk-return-001", "category": "INVESTING", "subtopic": "risk-return",
     "difficulty": "medium", "framing": "concept", "stem": "Higher expected return usually means?",
     "options": [
       {"id": "A", "text": "Higher risk", "is_correct": true, "distractor_rationale": "correct answer"},
       {"id": "B", "text": "Lower risk", "is_correct": false, "distractor_rationale": "d"},
       {"id": "C", "text": "No risk", "is_correct": false, "distractor_rationale": "d"},
       {"id": "D", "text": "A guaranteed loss", "is_correct": false, "distractor_rationale": "d"},
       {"id": "E", "text": "A fixed return", "is_correct": false, "distractor_rationale": "d"}],
     "correct_option_id": "A", "explanation": "Risk and expected return move together."},
    {"id": "TAX-capital-gains-001", "category": "TAXES", "subtopic": "capital-gains",
     "difficulty": "hard", "framing": "scenario", "stem": "Tax on a $1,000 gain at 15%?",
     "options": [
       {"id": "A", "text": "$0", "is_correct": false, "distractor_rationale": "d"},
       {"id": "B", "text": "$300", "is_correct": false, "distractor_rationale": "d"},
       {"id": "C", "text": "$1,000", "is_correct": false, "distractor_rationale": "d"},
       {"id": "D", "text": "$150", "is_correct": true, "distractor_rationale": "correct answer"}],
     "correct_option_id": "D", "explanation": "15% of $1,000 = $150."}
  ],
  "coverage_manifest": {},
  "self_check": {}
}
"""


def test_parses_and_is_valid():
    bank = parse_bank(SAMPLE, randomize_options=False)
    assert len(bank) == 3
    assert bank.validate() == []                       # valid; includes a 5-option item


def test_correct_answer_preserved_after_shuffle():
    bank = parse_bank(SAMPLE, randomize_options=False)
    for item in bank.items:
        correct_text = next(o.text for o in item.options if o.is_correct)
        shuffle_item_options(item, random.Random(123))
        # labels are contiguous A.. with no gaps
        assert [o.id for o in item.options] == list(VALID_OPTION_IDS[:len(item.options)])
        flagged = [o for o in item.options if o.is_correct]
        assert len(flagged) == 1                        # exactly one correct survives
        assert item.correct_option_id == flagged[0].id  # key points at it
        assert flagged[0].text == correct_text          # we only moved it, didn't change it
        assert item.validate() == []


def test_shuffle_spreads_the_correct_position():
    """The whole point: the correct letter must not stay glued to one slot."""
    r = random.Random(7)
    positions = []
    for _ in range(300):
        item = parse_bank(SAMPLE, randomize_options=False).items[0]   # correct starts at B
        shuffle_item_options(item, r)
        positions.append(item.correct_option_id)
    distinct = set(positions)
    assert len(distinct) >= 3                            # spread across several letters
    most = max(positions.count(p) for p in distinct)
    assert most < len(positions) * 0.6                   # no letter dominates (rough uniformity)


def test_parse_bank_randomizes_by_default():
    bank = parse_bank(SAMPLE)                            # randomize_options=True
    assert bank.validate() == []
    for item in bank.items:
        flagged = [o for o in item.options if o.is_correct]
        assert len(flagged) == 1 and item.correct_option_id == flagged[0].id


def test_all_four_option_bank_is_rejected():
    data = json.loads(SAMPLE)
    for it in data["items"]:                            # force every item down to 4 options
        it["options"] = it["options"][:4]
        if not any(o["is_correct"] for o in it["options"]):
            it["options"][0]["is_correct"] = True
            it["correct_option_id"] = it["options"][0]["id"]
    with pytest.raises(ValueError):
        parse_bank(json.dumps(data))


def test_quiz_scoring_and_gate():
    quiz = Quiz(parse_bank(SAMPLE), sort_by_difficulty=True)
    while not quiz.finished:
        item = quiz.current()
        res = quiz.submit_answer(item.correct_option_id)
        assert res["correct"]
    summary = quiz.results()
    assert summary["percent"] == 100.0 and summary["passed_gate"]


def test_gate_fails_below_threshold():
    quiz = Quiz(parse_bank(SAMPLE), sort_by_difficulty=True)
    quiz.submit_answer(quiz.current().correct_option_id)   # 1 right
    quiz.submit_answer("Z")                                # wrong
    quiz.submit_answer("Z")                                # wrong -> 1/3 = 33%
    assert not quiz.results()["passed_gate"]


def test_difficulty_sorted_easy_to_hard():
    quiz = Quiz(parse_bank(SAMPLE), sort_by_difficulty=True)
    assert [i.difficulty for i in quiz.items] == ["easy", "medium", "hard"]


def test_difficulty_labels_cover_all_tiers():
    assert set(DIFFICULTY_LABELS) == {"easy", "medium", "hard"}
    assert DIFFICULTY_LABELS["easy"] == "Beginner"


def test_topic_for_day_rotates_through_all_categories():
    assert topic_for_day(0) == CATEGORY_NAMES[0]
    assert topic_for_day(len(CATEGORY_NAMES)) == CATEGORY_NAMES[0]   # wraps around
    assert {topic_for_day(d) for d in range(len(CATEGORY_NAMES))} == set(CATEGORY_NAMES)


def test_build_prompt_scopes_to_one_topic():
    p = build_prompt(scope="INVESTING", questions_per_subtopic=3)
    assert "scope: INVESTING" in p and "questions_per_subtopic: 3" in p


def test_verdict_messages():
    assert verdict_message(0) == "YOU'RE FIRED"
    assert "PAYDAY" in verdict_message(80)
