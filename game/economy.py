"""Phases 2 & 3: Markets (asset values drift) and Interest (debts grow). Neither touches cash."""

import config
from .state import ASSET_CLASSES, DEBT_SLOTS
from .formulas import apply_return, accrue_interest


def phase_markets(state, rng) -> dict:
    applied = {}
    for cls in ASSET_CLASSES:
        balance = state.investments[cls]
        if balance > 0:
            r = rng.draw_normal(config.RETURNS[cls]["mu"], config.RETURNS[cls]["sigma"])
            state.investments[cls] = apply_return(balance, r)
            applied[cls] = r
    return applied


def phase_interest(state) -> None:
    # Grow interest for debts
    for slot in DEBT_SLOTS:
        liab = state.liabilities[slot]
        if liab is not None and liab["principal"] > 0:
            liab["principal"] = accrue_interest(liab["principal"], liab["apr"])
