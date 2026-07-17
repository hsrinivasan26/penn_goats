"""Drives one turn across Streamlit reruns.

Mirrors game.engine.run_turn, split at the player-choice point so the UI can show the
paycheck + event, take the player's actions, then finish the turn. Player actions (phase 6)
happen between begin_month() and end_month() via game.choices.* calls.

KEEP IN SYNC with game.engine.run_turn -- same phase order, same bookkeeping. (When the
engine settles, this could become an official interactive API in the engine itself.)
"""

from game.paystub import phase_income
from game.economy import phase_markets, phase_interest
from game.outflows import phase_forced_outflows
from game.events import phase_annual_tax, phase_life_event
from game.happiness import phase_happiness
from game.engine import phase_checks, check_milestones


def begin_month(state, rng):
    """Phases 1-5: income -> markets -> interest -> forced outflows -> tax -> life event.

    Returns the display payload the UI shows before the player acts.
    """
    if state.game_over is not None:
        return None
    state.reset_scratch()
    stub = phase_income(state)                                   # 1
    phase_markets(state, rng)                                    # 2
    phase_interest(state)                                        # 3
    bill = phase_forced_outflows(state)                          # 4
    state.consecutive_shortfalls = (
        state.consecutive_shortfalls + 1 if state.shortfall_flag else 0)
    tax = phase_annual_tax(state)                                # 5a
    event = phase_life_event(state, rng)                         # 5b
    return {"stub": stub, "bill": bill, "tax": tax, "event": event}


def end_month(state):
    """Phases 7-8 (phase 6 already applied via the player's clicks). Advances the turn."""
    if state.game_over is not None:
        return
    check_milestones(state)                                      # milestone bonus feeds phase 7
    phase_happiness(state)                                       # 7 (may end: burnout)
    if state.game_over is None:
        phase_checks(state)                                      # 8 (may end: bankruptcy/win/timeout)
    state.history.append(state.snapshot())
    if state.game_over is None:
        state.turn += 1
    state.validate()
