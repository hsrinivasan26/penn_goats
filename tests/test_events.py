"""Event-table sanity: probabilities, bucket validity, and forced effects."""

import config
from game.state import new_game
from game.rng import SeededRNG
from game.events import phase_life_event


def test_event_probabilities_sum_to_100():
    assert sum(b["prob"] for b in config.EVENTS) == 100


def test_roll_bucket_only_returns_valid_buckets():
    rng = SeededRNG(7)
    keys = {b["key"] for b in config.EVENTS}
    for _ in range(2000):
        assert rng.roll_bucket(config.EVENTS)["key"] in keys


def test_forced_layoff_sets_unemployed_and_clamps_cash():
    s = new_game("A")                          # starts with $500
    phase_life_event(s, SeededRNG(0), forced={"key": "large_neg", "amount": 1000})
    assert s.employed is False
    assert s.cash == 0                          # 500 - 1000 clamps at 0


def test_forced_raise_bumps_gross_and_adds_cash():
    s = new_game("A")
    s.gross_month = 3000                        # pin, so the test is independent of config tuning
    phase_life_event(s, SeededRNG(0), forced={"key": "large_pos", "amount": 1000})
    assert s.gross_month == 3300               # +10% durable raise
    assert s.cash == 1500                       # 500 + 1000


def test_no_random_event_on_the_first_turn():
    """Turn 1 is a grace month: the player is never greeted by a surprise event."""
    for seed in range(40):
        s = new_game("A", seed=seed)
        assert s.turn == 1
        assert phase_life_event(s, SeededRNG(seed)) is None
        assert s._event is None and s.cash == 500 and s.employed


def test_random_events_do_fire_after_the_first_turn():
    s = new_game("A", seed=3)
    s.turn = 2
    fired = {phase_life_event(s, SeededRNG(seed))["key"] for seed in range(60)}
    assert fired                                  # rolls happen again from turn 2 on


def test_forced_events_still_work_on_turn_1():
    s = new_game("A")
    desc = phase_life_event(s, SeededRNG(0), forced={"key": "small_neg", "amount": 100})
    assert desc["cash_delta"] == -100
