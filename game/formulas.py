"""Pure spec formulas: numbers in, numbers out, no game state. The single source for every calculation."""

import math
from decimal import Decimal, ROUND_HALF_UP
import config


def round_half_up(x) -> int:
    """Round to the nearest whole dollar, .5 going away from zero (not Python's banker's rounding)."""
    return int(Decimal(str(x)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def paystub(gross: int) -> dict:
    """gross -> {gross, federal, state, fica, net}. The gross->net teaching calculation."""
    federal = round_half_up(gross * config.FEDERAL_RATE)
    state = round_half_up(gross * config.STATE_RATE)
    fica = round_half_up(gross * config.FICA_RATE)
    return {"gross": gross, "federal": federal, "state": state, "fica": fica,
            "net": gross - federal - state - fica}


def apply_return(balance: int, r: float) -> int:
    """New asset value after a monthly return r (never below 0)."""
    return max(0, round_half_up(balance * (1 + r)))


def accrue_interest(principal: int, apr: float) -> int:
    """Principal after one month of interest."""
    return principal + round_half_up(principal * (apr / 12))


def min_payment(kind: str, principal: int) -> int:
    """Minimum monthly payment for a debt, capped at the remaining balance."""
    rule = config.MIN_PAYMENT.get(kind)
    if rule is None or principal <= 0:
        return 0
    return min(max(rule["floor"], round_half_up(rule["fraction"] * principal)), principal)


def capital_gain(amount_sold: int, cost_basis: int, balance: int):
    """Selling amount_sold from an asset worth `balance` -> (gain, basis_removed)."""
    frac = amount_sold / balance
    basis = round_half_up(cost_basis * frac)
    return amount_sold - basis, basis


def cap_gains_tax(gain: int) -> int:
    """Tax owed on a realized gain (0 if the sale was at a loss)."""
    return round_half_up(gain * config.CAP_GAINS_RATE) if gain > 0 else 0


def annual_reconciliation(annual_gross: int, withheld_ytd: int) -> int:
    """Year-end income-tax truing-up: positive = you owe, negative = refund."""
    return round_half_up(annual_gross * config.INCOME_TAX_RATE) - withheld_ytd


def leisure_happiness(spend: int) -> int:
    """Happiness bought by leisure spending, with diminishing (sqrt) returns."""
    return round_half_up(config.GAIN_SCALE * math.sqrt(spend))


def amortize(principal: int, monthly_rate: float, months: int) -> int:
    """Fixed monthly payment that fully repays `principal` over `months`."""
    if monthly_rate == 0:
        return round_half_up(principal / months)
    factor = (1 + monthly_rate) ** months
    return round_half_up(principal * monthly_rate * factor / (factor - 1))
