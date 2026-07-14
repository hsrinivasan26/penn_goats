import math
from typing import Dict, Optional

DECAY = 4
GAIN_SCALE = 1.5
STRESS_LIMIT = 1.0
STRESS_PENALTY = 5
SHORTFALL_PENALTY = 15
HAPPINESS_START = 60
#smb help this is claude+copilot+gemini code :(

def clamp(value: int, low: int, high: int) -> int:
    return max(low, min(high, value))


def display_happiness(value: int) -> str:
    """Return a readable string for the current happiness value."""
    return f"Happiness: {clamp(value, 0, 100)}/100"


def leisure_gain(leisure_spend: int) -> int:
    if leisure_spend <= 0:
        return 0
    return round(GAIN_SCALE * math.sqrt(leisure_spend))


def update_happiness(
    current_happiness: int,
    *,
    debt: float = 0,
    leisure_spend: int = 0,
    essentials_unmet: bool = False,
    random_event_delta: int = 0,
    gross_month: int = 0,
    debt_ratio: Optional[float] = None,
    milestone_bonus: int = 0,
) -> Dict[str, object]:
    """Apply the happiness pipeline for one turn.

    The order matches the game spec:
    decay -> stress penalty -> shortfall penalty -> leisure gain -> event/milestone -> clamp -> burnout.
    """

    if debt_ratio is None:
        debt_ratio = debt / max(1, gross_month * 12)

    h = current_happiness
    h -= DECAY

    if debt_ratio > STRESS_LIMIT:
        h -= STRESS_PENALTY

    if essentials_unmet:
        h -= SHORTFALL_PENALTY

    h += leisure_gain(leisure_spend)
    h += random_event_delta + milestone_bonus
    happiness = clamp(round(h), 0, 100)

    return {
        "happiness": happiness,
        "game_over": happiness <= 0,
    }
