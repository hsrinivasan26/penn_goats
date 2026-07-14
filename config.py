"""Every tunable constant, in one place. Change difficulty here, nowhere else. (Spec parameters table.)"""

# Game length & goal
TURN_LIMIT = 60            # months (5 years)
TARGET = 25_000           # net worth needed to win
BANKRUPTCY_SHORTFALL_STREAK = 3   # lose after this many months in a row failing to cover essentials

# Taxes / withholding (applied to gross pay)
FEDERAL_RATE = 0.12
STATE_RATE = 0.03
FICA_RATE = 0.0765
INCOME_TAX_RATE = 0.15    # federal + state; used for the year-end reconciliation
CAP_GAINS_RATE = 0.15

# Monthly investment returns, drawn from Normal(mu, sigma). sigma 0 = deterministic.
RETURNS = {
    "riskfree": {"mu": 0.003, "sigma": 0.000},
    "index":    {"mu": 0.007, "sigma": 0.030},
    "growth":   {"mu": 0.012, "sigma": 0.080},
    "crypto":   {"mu": 0.020, "sigma": 0.250},
    "home":     {"mu": 0.003, "sigma": 0.010},
}

# Debt APRs (monthly rate = APR / 12)
APR = {"student": 0.06, "mortgage": 0.065, "credit_card": 0.24, "auto": 0.09}

# Minimum monthly debt payment = max(floor, round(fraction * principal))
MIN_PAYMENT = {
    "student":     {"floor": 50, "fraction": 0.01},
    "credit_card": {"floor": 35, "fraction": 0.03},
}

# How heavily each debt kind bears on STRESS/happiness (Phase 7) -- separate from its
# interest rate (which is the cash-flow weight). "Good debt" (student, mortgage) is light;
# credit cards are the trap and weigh most. This NEVER directly loses you the game -- it
# only feeds the stress -> burnout channel. "tax" applies to unpaid tax_owed.
STRESS_WEIGHT = {
    "credit_card": 1.5,   # heaviest: 24% APR + the minimum-payment spiral
    "tax":         1.2,   # owing the IRS is urgent
    "auto":        0.8,   # secured but depreciating; repossession risk
    "mortgage":    0.10,  # "good debt" -- builds equity
    "student":     0.15,  # light, but still a real (small) drag
}

# Essentials (monthly). Trimmed from a $2000 baseline to give Path A room to survive.
ESSENTIALS = {"rent": 1100, "food": 380, "transport": 230, "utilities": 140}

# Happiness
DECAY = 4
GAIN_SCALE = 1.5          # leisure_happiness = round(1.5 * sqrt(spend))
STRESS_LIMIT = 0.35       # weighted-debt / annual-gross ratio above which stress applies
STRESS_PENALTY = 5
SHORTFALL_PENALTY = 15
HAPPINESS_START = 60

# Event table: exactly one bucket fires per turn; probs sum to 100.
# magnitude = inclusive [low, high] dollar range; sign = +/- direction.
# "quiet" = a calm month (nothing happens); "large_neg" = a rare layoff you must
# recover from by finding a new job (the change_job action).
EVENTS = [
    {"key": "quiet",     "prob": 30, "magnitude": [0, 0],      "sign": +1},
    {"key": "small_neg", "prob": 22, "magnitude": [50, 300],   "sign": -1},
    {"key": "mod_neg",   "prob": 8,  "magnitude": [300, 700],  "sign": -1, "gross_mult": 0.90},
    {"key": "large_neg", "prob": 1,  "magnitude": [800, 2000], "sign": -1, "set_unemployed": True},
    {"key": "small_pos", "prob": 22, "magnitude": [50, 300],   "sign": +1},
    {"key": "large_pos", "prob": 3,  "magnitude": [800, 3000], "sign": +1, "gross_mult": 1.10},
    {"key": "mood",      "prob": 14, "happiness_range": [-10, 10]},
]

# Starting scenarios (both early-career). Not the differentiation-guide's Path A/B.
# Per-path `target` calibrated so both paths win ~50% of the time under skilled
# play -- they differ because Path B earns far more, so it needs a higher bar to
# be *equally* difficult. See README "Balance" for how these were derived.
PATHS = {
    "A": {"gross_month": 3300, "cash": 500, "student_loan": None, "target": 23_000},
    "B": {"gross_month": 5000, "cash": 500,
          "student_loan": {"principal": 30_000, "apr": 0.06}, "target": 68_000},
}

# Big-move defaults (Phase 6)
MORTGAGE_TERM_MONTHS = 360
