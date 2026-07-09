"""Phase 8 checks + run_turn(), which chains all 8 phases. Also fires milestones from data/milestones.json."""

import json
import os
import config
from .enums import GameOver, Housing
from .paystub import phase_income
from .economy import phase_markets, phase_interest
from .outflows import phase_forced_outflows
from .events import phase_annual_tax, phase_life_event
from .happiness import phase_happiness

_DATA = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "data", "milestones.json"))
try:
    with open(_DATA, encoding="utf-8") as _f:
        MILESTONES = json.load(_f)
except (OSError, ValueError):
    MILESTONES = []


def phase_checks(state) -> None:
    """Phase 8: bankruptcy after a shortfall streak; win/timeout (by net worth) at the final turn.

    Note: negative net worth is NOT a loss -- starting adulthood with student debt is normal.
    You lose by failing to cover essentials repeatedly (below), or by burning out (Phase 7).
    """
    if state.consecutive_shortfalls >= config.BANKRUPTCY_SHORTFALL_STREAK:
        state.game_over = GameOver.BANKRUPTCY
    elif state.turn == config.TURN_LIMIT:
        state.game_over = GameOver.WIN if state.net_worth() >= state.target else GameOver.TIMEOUT


def _condition_met(state, when: dict) -> bool:
    for key, value in when.items():
        if key == "cash_at_least" and state.cash < value:
            return False
        if key == "net_worth_at_least" and state.net_worth() < value:
            return False
        if key == "owns_home" and (state.housing == Housing.OWN) != value:
            return False
    return True


def check_milestones(state) -> None:
    """Fire at most one not-yet-earned milestone this turn; its bonus feeds Phase 7."""
    for m in MILESTONES:
        if m["id"] in state.milestones_fired:
            continue
        if _condition_met(state, m.get("when", {})):
            state.milestone_bonus += m["bonus"]
            state.milestones_fired.append(m["id"])
            state._milestone = m
            break


def run_turn(state, rng, choose_actions=None, forced_event=None):
    """Run one full turn (Phases 1-8). choose_actions(state) makes the player's Phase-6 moves."""
    if state.game_over is not None:
        return state

    state.reset_scratch()
    phase_income(state)                                 # 1
    phase_markets(state, rng)                           # 2
    phase_interest(state)                               # 3
    phase_forced_outflows(state)                        # 4
    state.consecutive_shortfalls = (                    # track the streak for the bankruptcy rule
        state.consecutive_shortfalls + 1 if state.shortfall_flag else 0)
    phase_annual_tax(state)                             # 5a
    phase_life_event(state, rng, forced=forced_event)   # 5b
    if choose_actions is not None:
        choose_actions(state)                           # 6
    check_milestones(state)                             # milestone bonus feeds Phase 7
    phase_happiness(state)                              # 7 (may end the game: burnout)
    if state.game_over is None:
        phase_checks(state)                             # 8 (may end: bankruptcy/win/timeout)

    state.history.append(state.snapshot())
    if state.game_over is None:
        state.turn += 1
    state.validate()
    return state
