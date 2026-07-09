"""Phase 4: Forced outflows -- the shortfall mechanic where the need statement lives."""

import config
from .enums import DebtKind, Housing
from .formulas import min_payment


def required_outflow(state) -> dict:
    """The full 'what must leave cash this month' bill, computed without mutating anything."""
    housing = state.mortgage_payment if state.housing == Housing.OWN else state.rent
    essentials = housing + state.food + state.transport + state.utilities
    minimums = {}
    for slot in (DebtKind.STUDENT, DebtKind.CREDIT_CARD):
        liab = state.liabilities[slot]
        if liab is not None and liab["principal"] > 0:
            minimums[slot] = min_payment(liab["kind"], liab["principal"])
    return {"housing": housing, "essentials": essentials, "debt_minimums": minimums,
            "required": essentials + sum(minimums.values())}


def _ensure_credit_card(state) -> dict:
    if state.liabilities[DebtKind.CREDIT_CARD] is None:
        state.liabilities[DebtKind.CREDIT_CARD] = {
            "principal": 0, "apr": config.APR["credit_card"], "kind": DebtKind.CREDIT_CARD,
        }
    return state.liabilities[DebtKind.CREDIT_CARD]


def phase_forced_outflows(state) -> dict:
    """Pay essentials + debt minimums if cash allows; otherwise fall short and borrow the gap."""
    bill = required_outflow(state)
    required = bill["required"]

    if state.cash >= required:
        state.cash -= required
        state.shortfall_flag = False
        for slot, payment in bill["debt_minimums"].items():
            state.liabilities[slot]["principal"] -= payment
        if state.housing == Housing.OWN and state.liabilities[DebtKind.MORTGAGE] is not None:
            mort = state.liabilities[DebtKind.MORTGAGE]
            mort["principal"] -= min(state.mortgage_payment, mort["principal"])
        bill["shortfall"], bill["gap"] = False, 0
    else:
        state.shortfall_flag = True
        gap = required - state.cash
        state.cash = 0
        _ensure_credit_card(state)["principal"] += gap
        bill["shortfall"], bill["gap"] = True, gap

    return bill
