"""Every tunable constant, in one place. Change difficulty here, nowhere else. (Spec parameters table.)"""

# !!! IMPORTANT !!!
# I spent 4 hours hand tuning so that paths A/B are roughly equal in difficulty (50/50)
# If you have any issues with these, please consult the whole team as a whole!
#
# REBALANCE (mentor feedback): the game is now intentionally hard (~40% win under skilled
# play, not 50%). Happiness decays faster and can't be binged back up (leisure cap); random
# events are rarer (25%) and evenly weighted; targets were re-derived by simulation for the
# new job board. Paths A/B are still tuned to be roughly equal. Re-run the balance sim and
# check with the team before changing the happiness knobs, EVENTS, or PATHS targets.

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

# Essentials (monthly). Back to a $2,000 baseline: tighter months, especially early on.
ESSENTIALS = {"rent": 1200, "food": 400, "transport": 240, "utilities": 160}

# Happiness  (rebalanced for a harder game -- see README "Balance" / consult the team)
DECAY = 7                 # natural decay per month (was 4: happiness was too easy to hold)
GAIN_SCALE = 1.5          # leisure_happiness = round(1.5 * sqrt(spend))
LEISURE_HAPPINESS_CAP = 8 # max happiness a single month of leisure can buy -- can't be binged,
                          # so recovering from a happiness hole takes several steady months
STRESS_LIMIT = 0.35       # weighted-debt / annual-gross ratio above which stress applies
STRESS_PENALTY = 5
SHORTFALL_PENALTY = 15
HAPPINESS_START = 50      # was 60: a lower buffer makes the opening months genuinely risky

# Event table: exactly one bucket fires per turn; probs sum to 100.
# magnitude = inclusive [low, high] dollar range; sign = +/- direction.
# "quiet" = a calm month (nothing happens); "large_neg" = a rare layoff you must
# recover from by finding a new job (the change_job action).
# "match"  = employer 401(k) match ("free money" -- a small positive cash bump).
# "raise"  = a durable cost-of-living raise (gross_mult), the lifestyle-inflation
#            teaching moment (separate from the one-off windfall in large_pos).
# NOTE: match/raise were added AFTER the original 50/50 tuning. They pull 2% from
# small_pos and 2% from mood; a durable raise makes the game a touch easier, so
# RE-RUN the balance sim (python play.py --auto) and check with the team before shipping.
# Rebalanced: events now fire only 25% of months (quiet 75%), and the 25% is spread evenly
# across the eight event buckets (3.125% each). roll_bucket sums these floats to exactly 100.
EVENTS = [
    {"key": "quiet",     "prob": 75.0,  "magnitude": [0, 0],      "sign": +1},
    {"key": "small_neg", "prob": 3.125, "magnitude": [50, 300],   "sign": -1},
    {"key": "mod_neg",   "prob": 3.125, "magnitude": [300, 700],  "sign": -1, "gross_mult": 0.90},
    {"key": "large_neg", "prob": 3.125, "magnitude": [800, 2000], "sign": -1, "set_unemployed": True},
    {"key": "small_pos", "prob": 3.125, "magnitude": [50, 300],   "sign": +1},
    {"key": "match",     "prob": 3.125, "magnitude": [50, 250],   "sign": +1},
    {"key": "large_pos", "prob": 3.125, "magnitude": [800, 3000], "sign": +1, "gross_mult": 1.10},
    {"key": "raise",     "prob": 3.125, "magnitude": [50, 200],   "sign": +1, "gross_mult": 1.10},
    {"key": "mood",      "prob": 3.125, "happiness_range": [-10, 10]},
]

# Starting scenarios (both early-career). Not the differentiation-guide's Path A/B.
# REBALANCED for the tiered job board, then grounded: salaries in ui/jobs.py are
# early-career figures (the ladder tops out at $6,300/mo, not $7,200), essentials are
# $2,000/mo, and the targets below were re-derived by simulation (400 seeds, skilled
# play that climbs the ladder) to land at a 40% win rate on each path -- hard, with
# less-astronomical goals ("$150k by age 23" instead of $190k). gross_month is only
# the STARTING salary; players change jobs via the board. !!! Team: re-run the sim
# before retuning -- the job board makes these very sensitive.
PATHS = {
    "A": {"gross_month": 3300, "cash": 500, "student_loan": None, "target": 150_000},
    "B": {"gross_month": 4800, "cash": 500,
          "student_loan": {"principal": 30_000, "apr": 0.06}, "target": 168_000},
}

# Big-move defaults (Phase 6)
MORTGAGE_TERM_MONTHS = 360
