# PHASE 7: Happiness

import config
from .enums import GameOver
from .formulas import round_half_up, leisure_happiness


def phase_happiness(state) -> None:
    # Apply natural decay
    h = state.happiness - config.DECAY

    debt_ratio = state.weighted_debt() / max(1, state.gross_month * 12)
    if debt_ratio > config.STRESS_LIMIT:
        h -= config.STRESS_PENALTY
    if state.shortfall_flag:
        h -= config.SHORTFALL_PENALTY

    # Leisure lifts mood, but only up to a monthly cap -- you can't binge-buy happiness back,
    # so a dip takes several steady months (and money) to climb out of.
    h += min(config.LEISURE_HAPPINESS_CAP, leisure_happiness(state.leisure_spend))
    h += state.event_happiness_delta + state.milestone_bonus

    state.happiness = max(0, min(100, round_half_up(h)))
    if state.happiness <= 0:
        state.game_over = GameOver.BURNOUT
