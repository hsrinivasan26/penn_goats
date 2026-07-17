"""Tests for the UI's AI glue: the results coach and the daily quiz builder.

No live model calls -- a fake generator is injected, and the no-key paths exercise the
fallbacks. The ui/ folder is added to the path so these modules import like the app does.
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "ui"))

import coach            # noqa: E402
import quiz             # noqa: E402
from game.state import new_game        # noqa: E402
from game.enums import GameOver, DebtKind  # noqa: E402
from game.mcq import DIFFICULTY_ORDER, topic_for_day  # noqa: E402

_OUTCOME_ENUM = {"win": GameOver.WIN, "bankruptcy": GameOver.BANKRUPTCY,
                 "burnout": GameOver.BURNOUT, "timeout": GameOver.TIMEOUT}


def _finished_state(outcome="win", cash=70_000):
    s = new_game("B", seed=1)
    s.liabilities[DebtKind.STUDENT] = None      # clear the loan so net worth == cash
    s.cash = cash
    s.happiness = 80
    s.turn = 60
    s.game_over = _OUTCOME_ENUM[outcome]
    s.history = [{"turn": i + 1, "net_worth": int(-29500 + 1650 * i), "cash": 0,
                  "happiness": 70, "employed": True, "shortfall": False,
                  "gross_month": 5000, "event": None} for i in range(60)]
    return s


# ---- coach -----------------------------------------------------------------

def test_coach_fallback_without_generator_or_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    text, is_ai = coach.overview(_finished_state("win"), "win")
    assert is_ai is False and "buffer" in text


def test_coach_uses_generator_output():
    text, is_ai = coach.overview(_finished_state("win"), "win",
                                 generator=lambda p: "Nice — you hit your goal.")
    assert is_ai is True and text == "Nice — you hit your goal."


def test_coach_falls_back_on_generator_error():
    def boom(_):
        raise RuntimeError("no api")
    text, is_ai = coach.overview(_finished_state("burnout"), "burnout", generator=boom)
    assert is_ai is False and "ground" in text


def test_coach_falls_back_on_empty_output():
    text, is_ai = coach.overview(_finished_state("timeout"), "timeout", generator=lambda p: "   ")
    assert is_ai is False


def test_coach_prompt_is_grounded_in_real_figures():
    s = _finished_state("win")
    seen = {}
    coach.overview(s, "win", generator=lambda p: seen.setdefault("p", p) or "ok")
    assert f"final_net_worth={s.net_worth()}" in seen["p"]
    assert f"goal={s.target}" in seen["p"] and "months_played=60" in seen["p"]


# ---- daily quiz ------------------------------------------------------------

_FAKE = {
    "items": [
        {"id": "T-a-1", "stem": "q1", "difficulty": "easy",
         "options": [{"id": "A", "text": "x", "is_correct": True},
                     {"id": "B", "text": "y", "is_correct": False},
                     {"id": "C", "text": "z", "is_correct": False},
                     {"id": "D", "text": "w", "is_correct": False}],
         "correct_option_id": "A"},
        {"id": "T-a-2", "stem": "q2", "difficulty": "hard",
         "options": [{"id": "A", "text": "x", "is_correct": False},
                     {"id": "B", "text": "y", "is_correct": True},
                     {"id": "C", "text": "z", "is_correct": False},
                     {"id": "D", "text": "w", "is_correct": False},
                     {"id": "E", "text": "v", "is_correct": False}],
         "correct_option_id": "B"},
    ]
}


def test_quiz_falls_back_when_not_prefetched(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    quiz.clear_cache()
    topic, bank, used_ai = quiz.build_daily_quiz(day=1, seed=0)
    assert used_ai is False
    assert 8 <= len(bank.items) <= 10                   # random 8-10 from the fallback bank
    order = [DIFFICULTY_ORDER.get(i.difficulty.lower(), 99) for i in bank.items]
    assert order == sorted(order)                       # easy -> hard ramp
    assert bank.validate() == []


def test_quiz_length_is_random_8_to_10(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    quiz.clear_cache()
    lengths = {len(quiz.build_daily_quiz(day=5, seed=s)[1].items) for s in range(25)}
    assert lengths and all(8 <= L <= 10 for L in lengths)


def test_quiz_uses_prefetched_ai_bank():
    quiz.clear_cache()
    topic = topic_for_day(0)
    quiz._prime(topic, generator=lambda p: json.dumps(_FAKE))   # synchronous prime into cache
    assert quiz.is_ready(0)
    _, bank, used_ai = quiz.build_daily_quiz(day=0, seed=0)
    assert used_ai is True and bank.validate() == []


def test_prefetch_marks_topic_ready_then_clears():
    quiz.clear_cache()
    assert not quiz.is_ready(0)
    quiz._prime(topic_for_day(0), generator=lambda p: json.dumps(_FAKE))
    assert quiz.is_ready(0)
    quiz.clear_cache()
    assert not quiz.is_ready(0)


def test_quiz_topic_matches_the_day():
    quiz.clear_cache()
    topic, _, _ = quiz.build_daily_quiz(day=3, seed=0)
    assert topic == topic_for_day(3)
