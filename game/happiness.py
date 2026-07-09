# PHASE 7: Happiness

import config
from .enums import GameOver
from .formulas import round_half_up, leisure_happiness


def phase_happiness(state) -> None:
    # Apply natural decay
    h = state.happiness - config.DECAY

    # Subtract stress and shortfall penalties
    debt_ratio = state.liabilities_total() / max(1, state.gross_month * 12)
    if debt_ratio > config.STRESS_LIMIT:
        h -= config.STRESS_PENALTY
    if state.shortfall_flag:
        h -= config.SHORTFALL_PENALTY

    # Add leisure/event gains
    h += leisure_happiness(state.leisure_spend)
    h += state.event_happiness_delta + state.milestone_bonus

    # Clamp to 100. Happiness can't go over 100!
    state.happiness = max(0, min(100, round_half_up(h)))
    if state.happiness <= 0:
        state.game_over = GameOver.BURNOUT
