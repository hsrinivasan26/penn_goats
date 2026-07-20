"""Career model for the job board.

Jobs come from a fixed, tiered catalog instead of a free salary box. Which tiers a player
can take is gated two ways (whichever is higher wins):

  * education floor  -- your starting path. No degree (path A) starts at the Entry tier;
    a graduate (path B) starts already qualified for the Skilled tier.
  * experience       -- months of work you actually PERFORMED. The monthly money quiz IS
    the job: passing it logs that month of experience. Coasting past a month (skipping or
    failing the quiz) still pays the salary, but the career doesn't move -- you can't get
    promoted for work you didn't do.

Everything here is pure data + pure functions (no Streamlit, no engine mutation), so it's
easy to unit-test and the dialog just renders what these return.
"""

# tier -> player-facing name
TIER_NAMES = {0: "Entry", 1: "Skilled", 2: "Professional"}

# months of performed work (passed quizzes) that add +1 / +2 tiers on top of the education floor
EXP_FOR_TIER = {1: 12, 2: 30}

# The catalog. Salaries are monthly gross. Kept deliberately spread so upgrading matters.
JOBS = [
    {"title": "Retail associate",       "gross": 2400, "tier": 0},
    {"title": "Barista",                "gross": 2600, "tier": 0},
    {"title": "Warehouse packer",       "gross": 2900, "tier": 0},
    {"title": "Junior office admin",    "gross": 3300, "tier": 0},
    {"title": "Bookkeeper",             "gross": 3800, "tier": 1},
    {"title": "Dental assistant",       "gross": 4200, "tier": 1},
    {"title": "IT support specialist",  "gross": 4600, "tier": 1},
    {"title": "Licensed practical nurse", "gross": 5000, "tier": 1},
    {"title": "Data analyst",           "gross": 5600, "tier": 2},
    {"title": "Registered nurse",       "gross": 6400, "tier": 2},
    {"title": "Software engineer",      "gross": 7200, "tier": 2},
]

# The job each starting path begins in (its gross matches config.PATHS[path]["gross_month"]).
START_TITLE = {"A": "Junior office admin", "B": "Licensed practical nurse"}


def education_floor(path: str) -> int:
    """Tier a player qualifies for on day one, from their degree status."""
    return 1 if path == "B" else 0


def experience_bonus(months_worked: int) -> int:
    """Extra tiers unlocked purely by tenure."""
    bonus = 0
    for tier, need in EXP_FOR_TIER.items():
        if months_worked >= need:
            bonus = max(bonus, tier)
    return bonus


def available_tier(path: str, months_worked: int) -> int:
    """Highest tier the player can take right now (capped at the top tier)."""
    return min(max(TIER_NAMES), education_floor(path) + experience_bonus(months_worked))


def offerings(path: str, months_worked: int) -> list:
    """Jobs the player qualifies for, cheapest first."""
    top = available_tier(path, months_worked)
    return [j for j in JOBS if j["tier"] <= top]


def locked_tiers(path: str, months_worked: int) -> list:
    """Tiers not yet unlocked, for showing what's still ahead."""
    top = available_tier(path, months_worked)
    return [t for t in sorted(TIER_NAMES) if t > top]


def requirement_text(tier: int) -> str:
    """Plain-English unlock rule for a tier the player hasn't reached."""
    need = EXP_FOR_TIER.get(tier)
    if tier == 1:
        return f"a degree, or {need} months of work experience"
    if tier == 2:
        return f"a degree + experience, or {need} months of work experience"
    return "already available"


def next_unlock(path: str, months_worked: int):
    """(tier_name, months_remaining) for the next tier that tenure will unlock, or None.

    Accounts for the education floor: a graduate (floor 1) only needs +1 experience tier to
    reach Professional, so the countdown is shorter than for a non-graduate.
    """
    locked = locked_tiers(path, months_worked)
    if not locked:
        return None
    tier = locked[0]
    need_bonus = tier - education_floor(path)        # experience tiers still required
    need_months = EXP_FOR_TIER.get(need_bonus)
    if need_months is None:
        return None
    return TIER_NAMES[tier], max(0, need_months - months_worked)


def title_for_gross(gross: int):
    """Best-guess catalog title for a salary (used to label the current job)."""
    for j in JOBS:
        if j["gross"] == gross:
            return j["title"]
    return None
