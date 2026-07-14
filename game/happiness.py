"""Phase 7: Happiness -- the anti-hoarding pressure that forces you to spend a little."""

import config
from .enums import GameOver
from .formulas import round_half_up, leisure_happiness


def phase_happiness(state) -> None:
    """Decay, then stress/shortfall penalties, then leisure + event/milestone gains, then clamp 0-100."""
    h = state.happiness - config.DECAY

    debt_ratio = state.weighted_debt() / max(1, state.gross_month * 12)
    if debt_ratio > config.STRESS_LIMIT:
        h -= config.STRESS_PENALTY
    if state.shortfall_flag:
        h -= config.SHORTFALL_PENALTY

    h += leisure_happiness(state.leisure_spend)
    h += state.event_happiness_delta + state.milestone_bonus

    state.happiness = max(0, min(100, round_half_up(h)))
    if state.happiness <= 0:
        state.game_over = GameOver.BURNOUT
