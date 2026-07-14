"""
investments.py

Handles investing for the game: lets a player put cash into different
asset classes, and rolls each asset's return once per turn.

WHERE THE CASH COMES FROM: this file doesn't generate money itself --
player["cash"] is a shared value. paystub.py's run_paycheck_phase() is
what actually deposits money into player["cash"] (net pay, after
withholdings, each pay period). make_investment() below then draws from
that same cash balance. So the real flow, in order, is:

    paystub.run_paycheck_phase(player)   # adds net pay to player["cash"]
              |
              v
    investments.make_investment(player, ...)  # moves some of that cash into
                                                # an asset class

If a player isn't employed (see paystub.py), player["cash"] simply won't
be growing from paychecks -- they can still invest whatever cash they
already have (savings, a windfall from a life event, etc.), there's just
no new paycheck money coming in to fund further investing.

IMPORTANT DESIGN NOTE: rolled returns only change the INVESTMENT SLIDER
VALUE (the dollar amount sitting inside that asset). They never touch
cash directly -- a gain or loss just makes the investments slider go up
or down. Cash only changes when the player actively invests (moves cash
IN) or sells (moves it back OUT, handled elsewhere / in a future file).

Interest/return rates here are randomized per turn for gameplay purposes
-- they are NOT pulled from real market data or actual current interest
rates. Think of them as "what this asset class typically behaves like,"
not a live feed.
"""

import random

# ============================================================
# ASSET CLASSES
# ============================================================
# Each entry explains, in plain language, what the asset actually is --
# meant to be shown to the player (e.g. as a tooltip or info popup) so
# they understand what they're choosing, not just a label on a slider.

ASSET_INFO = {
    "CD": {
        "display_name": "Certificate of Deposit (CD) — simulated",
        "description": (
            "A CD is essentially a promise: you lock money away for a set "
            "period, and in exchange a bank guarantees you a small, fixed "
            "return. It's about as close to risk-free investing gets -- you "
            "basically can't lose money, but you also won't make much. "
            "This is a fictional in-game asset, not a real financial product."
        ),
        "risk_level": "very low",
    },
    "INDEX_FUND": {
        "display_name": "Index Fund — simulated",
        "description": (
            "An index fund is a big basket of many companies' stocks bundled "
            "together (like 'the 500 biggest US companies'), so you're not "
            "betting on any single company -- you're betting on the market as "
            "a whole. Historically it grows steadily over time, but it can "
            "still drop when the overall economy has a bad stretch. "
            "This is a fictional in-game asset, not a real fund."
        ),
        "risk_level": "medium",
    },
    "GROWTH_STOCK": {
        "display_name": "Growth Stocks — simulated",
        "description": (
            "Buying stock in a single company (or a handful of them) betting "
            "they'll grow fast. The upside can be much bigger than an index "
            "fund, but so can the downside -- one company's bad news can hit "
            "you a lot harder than it would hit a diversified fund. "
            "This is a fictional in-game asset, not a real company's stock."
        ),
        "risk_level": "high",
    },
    "CRYPTO": {
        "display_name": "Cryptocurrency — simulated",
        "description": (
            "A digital currency (like Bitcoin) whose price swings are driven "
            "heavily by speculation and sentiment rather than earnings or "
            "fundamentals. It can post huge gains fast -- and lose most of "
            "its value just as fast. Going all-in on crypto is a classic way "
            "to blow up a portfolio. This is a fictional in-game asset, not "
            "a real cryptocurrency -- no real money ever leaves the game."
        ),
        "risk_level": "very high",
    },
    "PROPERTY": {
        "display_name": "Property (Home Equity) — simulated",
        "description": (
            "Owning real estate. Property values usually creep up slowly and "
            "steadily over the long run (this is 'home equity' building up), "
            "with far less day-to-day volatility than stocks -- but it's also "
            "not something you can quickly sell for cash if you suddenly need "
            "money, and prices can still drop in a housing downturn. "
            "This is a fictional in-game asset, not a real property."
        ),
        "risk_level": "low",
    },
}


def get_asset_descriptions():
    """Returns the ASSET_INFO dict for the frontend to render as
    explanations/tooltips before the player chooses what to invest in."""
    return ASSET_INFO


# ============================================================
# RETURN-ROLLING RULES (per turn, per asset class)
# ============================================================
# All ranges are PER-TURN percentage changes, randomized for gameplay --
# not real interest/market rates.

CD_RETURN_RANGE = (0.0005, 0.0015)          # always small and positive

INDEX_FUND_UP_PROB = 0.75                    # mostly up
INDEX_FUND_UP_RANGE = (0.001, 0.015)
INDEX_FUND_DOWN_RANGE = (-0.03, -0.001)      # occasional dip when "market tanks"

GROWTH_STOCK_UP_PROB = 0.55                  # high volatility, roughly a coinflip
GROWTH_STOCK_UP_RANGE = (0.001, 0.10)
GROWTH_STOCK_DOWN_RANGE = (-0.08, -0.001)

CRYPTO_UP_PROB = 0.50                        # very high volatility
CRYPTO_UP_RANGE = (0.001, 0.30)
CRYPTO_DOWN_RANGE = (-0.25, -0.001)
# Over-allocation punishment: the more of the TOTAL portfolio sitting in
# crypto, the higher the chance of an extra "crash on top of the crash"
# and the harder that extra crash hits. Encourages diversification instead
# of going all-in on the highest-volatility asset.
CRYPTO_OVERALLOCATION_THRESHOLD = 0.40       # beyond 40% of total invested $
CRYPTO_OVERALLOCATION_EXTRA_CRASH_CHANCE = 0.20
CRYPTO_OVERALLOCATION_EXTRA_CRASH_RANGE = (-0.20, -0.05)

PROPERTY_UP_PROB = 0.90                      # slow, steady appreciation most turns
PROPERTY_UP_RANGE = (0.0005, 0.004)
PROPERTY_DOWN_RANGE = (-0.03, -0.005)        # rare housing downturn


# ============================================================
# INDIVIDUAL ROLL FUNCTIONS
# ============================================================

def roll_cd_return():
    return random.uniform(*CD_RETURN_RANGE)


def roll_index_fund_return():
    if random.random() < INDEX_FUND_UP_PROB:
        return random.uniform(*INDEX_FUND_UP_RANGE)
    return random.uniform(*INDEX_FUND_DOWN_RANGE)


def roll_growth_stock_return():
    if random.random() < GROWTH_STOCK_UP_PROB:
        return random.uniform(*GROWTH_STOCK_UP_RANGE)
    return random.uniform(*GROWTH_STOCK_DOWN_RANGE)


def roll_crypto_return(crypto_allocation_fraction=0.0):
    """
    crypto_allocation_fraction = this asset's $ / total invested $ across
    ALL asset classes. Used to punish over-concentration in crypto.
    """
    if random.random() < CRYPTO_UP_PROB:
        pct_change = random.uniform(*CRYPTO_UP_RANGE)
    else:
        pct_change = random.uniform(*CRYPTO_DOWN_RANGE)

    if crypto_allocation_fraction > CRYPTO_OVERALLOCATION_THRESHOLD:
        if random.random() < CRYPTO_OVERALLOCATION_EXTRA_CRASH_CHANCE:
            pct_change += random.uniform(*CRYPTO_OVERALLOCATION_EXTRA_CRASH_RANGE)

    return pct_change


def roll_property_return():
    if random.random() < PROPERTY_UP_PROB:
        return random.uniform(*PROPERTY_UP_RANGE)
    return random.uniform(*PROPERTY_DOWN_RANGE)


ROLL_FUNCTIONS = {
    "CD": lambda frac: roll_cd_return(),
    "INDEX_FUND": lambda frac: roll_index_fund_return(),
    "GROWTH_STOCK": lambda frac: roll_growth_stock_return(),
    "CRYPTO": lambda frac: roll_crypto_return(frac),
    "PROPERTY": lambda frac: roll_property_return(),
}


# ============================================================
# INVESTING (moving cash IN -- does not touch the return rolls above)
# ============================================================

def make_investment(player, asset_type, amount):
    """
    Moves `amount` of cash into the given asset class. This is the only
    way money enters an investment -- the turn-based rolls below only
    grow or shrink what's already invested, they never add new principal.
    """
    if asset_type not in ASSET_INFO:
        raise ValueError(f"Unknown asset type: {asset_type}")
    if amount <= 0:
        raise ValueError("Investment amount must be positive.")
    if player["cash"] < amount:
        raise ValueError("Not enough cash to make this investment.")

    player["cash"] -= amount
    player["investments"][asset_type] = player["investments"].get(asset_type, 0.0) + amount


# ============================================================
# PHASE: ROLL THIS TURN'S RETURNS
# ============================================================

def roll_all_investments(player):
    """
    For every asset class the player currently owns (amount > 0), rolls
    this turn's return and updates that asset's dollar amount.

    IMPORTANT: this function ONLY changes player["investments"][...] --
    the investment slider value. It never touches player["cash"]. Gains
    stay invested; losses shrink what's invested. Cash only moves via
    make_investment() (buying in) or a future sell function (cashing out).

    Returns a per-asset breakdown for the UI to display.
    """
    investments = player["investments"]
    total_invested = sum(investments.values())

    breakdown = {}
    for asset_type, amount in list(investments.items()):
        if amount <= 0:
            continue

        allocation_fraction = (amount / total_invested) if total_invested > 0 else 0.0
        pct_change = ROLL_FUNCTIONS[asset_type](allocation_fraction)

        old_amount = amount
        new_amount = max(0.0, amount * (1 + pct_change))
        investments[asset_type] = new_amount

        breakdown[asset_type] = {
            "display_name": ASSET_INFO[asset_type]["display_name"],
            "old_amount": round(old_amount, 2),
            "new_amount": round(new_amount, 2),
            "pct_change": round(pct_change * 100, 2),
            "dollar_change": round(new_amount - old_amount, 2),
        }

    new_total = sum(investments.values())
    return {
        "per_asset": breakdown,
        "investment_slider_total": round(new_total, 2),  # this is the only slider that moves
    }
