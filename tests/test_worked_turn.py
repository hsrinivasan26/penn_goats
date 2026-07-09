"""Acceptance tests: the spec's worked examples must match to the dollar."""

from game.state import new_game
from game.rng import SeededRNG
from game.formulas import paystub
from game.outflows import phase_forced_outflows
from game.economy import phase_interest
from game import choices
from game.engine import run_turn
from game.enums import DebtKind


def test_paystub_path_a():
    assert paystub(3000) == {"gross": 3000, "federal": 360, "state": 90, "fica": 230, "net": 2320}


def _pin_spec_numbers(s):
    """Pin the exact inputs the spec's worked examples assumed, so these tests verify
    the engine math and don't drift when config.py is tuned for balance."""
    s.gross_month = 3000
    s.rent, s.food, s.transport, s.utilities = 1200, 400, 250, 150


def test_worked_turn_1():
    """Example 1: Path A, turn 1, forced $150 car repair, then leisure 100 + invest 200 index."""
    s = new_game("A", seed=1)
    _pin_spec_numbers(s)

    def choose(state):
        choices.leisure(state, 100)
        choices.invest(state, 200, "index")

    run_turn(s, SeededRNG(1), choose_actions=choose,
             forced_event={"key": "small_neg", "amount": 150})

    assert s.cash == 370
    assert s.happiness == 71
    assert s.investments["index"] == 200
    assert s.net_worth() == 570
    assert s.shortfall_flag is False
    assert s.turn == 2


def test_shortfall_branch():
    """Example 2: cash 1500 < 2000 required -> borrow 500 onto a new credit card; +interest -> 510."""
    s = new_game("A")
    _pin_spec_numbers(s)
    s.cash = 1500
    bill = phase_forced_outflows(s)
    assert bill["gap"] == 500
    assert s.cash == 0
    assert s.shortfall_flag is True
    assert s.liabilities[DebtKind.CREDIT_CARD]["principal"] == 500
    phase_interest(s)
    assert s.liabilities[DebtKind.CREDIT_CARD]["principal"] == 510


def test_capital_gains_on_sell():
    """Example 3: index 400 (basis 200), sell 100 -> gain 50 -> capital-gains tax 8."""
    s = new_game("A")
    s.investments["index"] = 400
    s.cost_basis["index"] = 200
    s.cash = 0
    assert choices.sell(s, 100, "index") is True
    assert s.investments["index"] == 300
    assert s.cost_basis["index"] == 150
    assert s.cash == 100
    assert s.capital_gains_owed == 8
