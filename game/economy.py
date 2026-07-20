# PHASE 2 and PHASE 3
# Market drifting and interest stuff

import config
from .state import ASSET_CLASSES, DEBT_SLOTS
from .formulas import apply_return, accrue_interest


def phase_markets(state, rng) -> dict:
    applied = {}
    for cls in ASSET_CLASSES:
        balance = state.investments[cls]
        if balance > 0:
            spec = config.RETURNS[cls]
            r = rng.draw_normal(spec["mu"], spec["sigma"])
            crash_p = spec.get("crash_prob")
            if crash_p and rng.draw_int(1, 10_000) <= round(crash_p * 10_000):
                lo, hi = spec["crash_range"]            # fat left tail: a visible crash month
                r = rng.draw_int(round(lo * 100), round(hi * 100)) / 100
            state.investments[cls] = apply_return(balance, r)
            applied[cls] = r
    return applied


def phase_interest(state) -> None:
    # Grow interest for debts
    for slot in DEBT_SLOTS:
        liab = state.liabilities[slot]
        if liab is not None and liab["principal"] > 0:
            liab["principal"] = accrue_interest(liab["principal"], liab["apr"])
