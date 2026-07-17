"""The spec invariants must hold after every turn, across many seeded games."""

import config
from game.state import new_game
from game.rng import SeededRNG
from game.enums import GameOver
from game import choices
from game.engine import run_turn


def _simple_strategy(state):
    choices.leisure(state, 50)
    if state.cash > 1000:
        choices.invest(state, 200, "index")


def test_invariants_hold_over_full_games():
    for seed in range(25):
        s = new_game("A" if seed % 2 == 0 else "B", seed=seed)
        rng = SeededRNG(seed)
        for _ in range(70):                    # more than TURN_LIMIT; stops at game_over
            run_turn(s, rng, choose_actions=_simple_strategy)
            s.validate()                        # cash>=0, happiness 0-100, no negative balances
            assert s.net_worth() == s.cash + s.investments_total() - s.liabilities_total()
            if s.game_over:
                break


def test_unemployed_shortfalls_never_go_negative():
    s = new_game("A", seed=3)
    s.employed = False                          # no income -> guaranteed shortfalls
    rng = SeededRNG(3)
    for _ in range(12):
        run_turn(s, rng)
        assert s.cash >= 0
        if s.game_over:
            break


def test_game_stops_after_game_over():
    s = new_game("A", seed=5)
    s.employed = False
    rng = SeededRNG(5)
    while not s.game_over:
        run_turn(s, rng)
    frozen_turn = s.turn
    run_turn(s, rng)                            # should be a no-op once the game is over
    assert s.turn == frozen_turn


def test_path_b_survives_turn_1():
    """The whole point of the bankruptcy rule change: student debt is not instant death."""
    s = new_game("B", seed=2)
    run_turn(s, SeededRNG(2), forced_event={"key": "small_pos", "amount": 100})
    assert s.game_over is None                  # not bankrupt...
    assert s.net_worth() < 0                     # ...even though net worth is deep in student debt
    assert s.turn == 2


def test_win_fires_the_moment_the_goal_is_reached():
    """Reaching the net-worth goal wins immediately -- not only at the final month."""
    s = new_game("A", seed=1)
    s.cash = s.target + 50_000                   # already well past the goal
    run_turn(s, SeededRNG(1))
    assert s.game_over == GameOver.WIN
    assert s.turn < config.TURN_LIMIT            # won long before month 60


def test_bankruptcy_comes_from_a_shortfall_streak():
    """Lose after 3 months in a row failing to cover essentials -- not from negative net worth."""
    s = new_game("A", seed=9)
    s.employed = False                          # no income -> guaranteed shortfalls
    for _ in range(5):
        run_turn(s, SeededRNG(9), forced_event={"key": "small_pos", "amount": 50})
        if s.game_over:
            break
    assert s.game_over == GameOver.BANKRUPTCY
    assert s.consecutive_shortfalls == 3
    assert s.turn == 3                           # survived 1 and 2, lost on the 3rd
