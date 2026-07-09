# PHASE 6: What does the player do with leftover cash?
# Invalid moves become no-ops (don't do anything and return False)

import config
from .enums import AssetClass, DebtKind, Housing
from .formulas import capital_gain, cap_gains_tax, amortize


# THE BIG FOUR MOVES

def invest(state, amount: int, cls) -> bool:
    # Cash -> investment
    # cost_basis tracks what is paid (for capital gains)
    if cls not in state.investments or not (0 < amount <= state.cash):
        return False
    state.cash -= amount
    state.investments[cls] += amount
    state.cost_basis[cls] += amount
    return True


def sell(state, amount: int, cls) -> bool:
    # Sell assets / (Investment - tax) -> cash
    balance = state.investments.get(cls, 0)
    if not (0 < amount <= balance):
        return False
    gain, basis = capital_gain(amount, state.cost_basis[cls], balance)
    state.investments[cls] -= amount
    state.cost_basis[cls] -= basis
    state.cash += amount
    state.capital_gains_owed += cap_gains_tax(gain)
    return True


def leisure(state, amount: int) -> bool:
    if not (0 < amount <= state.cash):
        return False
    state.cash -= amount
    state.leisure_spend += amount
    return True


def pay_debt(state, amount: int, slot) -> bool:
    liab = state.liabilities.get(slot)
    if liab is None:
        return False
    cap = min(state.cash, liab["principal"])
    if not (0 < amount <= cap):
        return False
    state.cash -= amount
    liab["principal"] -= amount
    return True


# MOVES WITH REAL IMPACT

def take_loan(state, principal: int, apr: float, kind) -> bool:
    """Borrow cash into one of the schema's debt slots (student/mortgage/credit_card)."""
    if kind not in state.liabilities or principal <= 0:
        return False
    state.cash += principal
    existing = state.liabilities[kind]
    if existing is None:
        state.liabilities[kind] = {"principal": principal, "apr": apr, "kind": kind}
    else:
        existing["principal"] += principal
    return True

# TODO: Why is this here?
def go_to_school(state, cost: int) -> bool:
    """Take a student loan. (Whether/when graduation raises gross is an open team decision.)"""
    return take_loan(state, cost, config.APR["student"], DebtKind.STUDENT)


def buy_house(state, price: int, down: int) -> bool:
    """Convert to owning: pay a down payment, take a mortgage, gain a home asset."""
    if down < 0 or down > state.cash or price < down:
        return False
    state.cash -= down
    state.housing = Housing.OWN
    loan = price - down
    apr = config.APR["mortgage"]
    state.liabilities[DebtKind.MORTGAGE] = {"principal": loan, "apr": apr, "kind": DebtKind.MORTGAGE}
    state.mortgage_payment = amortize(loan, apr / 12, config.MORTGAGE_TERM_MONTHS)
    state.investments[AssetClass.HOME] += loan          # spec: home asset = financed amount
    state.cost_basis[AssetClass.HOME] += loan
    return True


def change_job(state, new_gross: int) -> bool:
    """Switch to a new monthly gross (and become employed again if you weren't)."""
    if new_gross <= 0:
        return False
    state.gross_month = new_gross
    state.employed = True
    return True


def buy_car(state, price: int) -> bool:
    """MVP: cash purchase only. Loan-financed autos need an 'auto' debt slot (open item)."""
    if not (0 < price <= state.cash):
        return False
    state.cash -= price
    return True
