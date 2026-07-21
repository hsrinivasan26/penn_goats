# PHASE 7: Happiness

import config
from .enums import GameOver
from .formulas import round_half_up


def phase_happiness(state) -> None:
    # Decay accelerates the longer the player holds off on leisure: base the month you
    # treat yourself, multiplied for every consecutive month you don't. Spending anything
    # on fun resets the spiral, so happiness is a recurring budget line you can't defer
    # for long.
    if state.leisure_spend > 0:
        state.months_without_leisure = 0
    decay = min(config.DECAY_MAX,
                round_half_up(config.DECAY_BASE * config.DECAY_GROWTH ** state.months_without_leisure))
    if state.leisure_spend == 0:
        state.months_without_leisure += 1
    h = state.happiness - decay

    debt_ratio = state.weighted_debt() / max(1, state.gross_month * 12)
    if debt_ratio > config.STRESS_LIMIT:
        h -= config.STRESS_PENALTY
    if state.shortfall_flag:
        h -= config.SHORTFALL_PENALTY

    # Leisure's happiness gain was already applied the moment the player spent (see
    # choices.leisure -- capped there, so the UI responds instantly). Here we only add
    # the event/milestone effects.
    h += state.event_happiness_delta + state.milestone_bonus

    state.happiness = max(0, min(100, round_half_up(h)))
    if state.happiness <= 0:
        state.game_over = GameOver.BURNOUT
