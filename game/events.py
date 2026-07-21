# PHASE 5: Annual tax bill
# Specifications in data/events.json
# Sizes/probabilities in config.EVENTS

import json
import os
import config
from .formulas import round_half_up, tax_breakdown
from .outflows import _ensure_credit_card

_DATA = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "data", "events.json"))
_LABELS = {}
try:
    with open(_DATA, encoding="utf-8") as _f:
        _LABELS = {k: v for k, v in json.load(_f).items() if not k.startswith("_")}
except (OSError, ValueError):
    _LABELS = {}


def _bucket_by_key(key: str) -> dict:
    for bucket in config.EVENTS:
        if bucket["key"] == key:
            return bucket
    raise KeyError(f"unknown event bucket: {key}")


def _label_for(key: str, turn: int) -> str:
    scenarios = _LABELS.get(key)
    return scenarios[turn % len(scenarios)] if scenarios else key.replace("_", " ")


def phase_annual_tax(state):
    """At a year boundary, true-up the year's taxes and settle what cash allows.

    The liability is progressive (standard deduction + marginal federal brackets + flat
    state); withholding was flat, so wage income usually over-withholds -> a REFUND paid
    into cash. Capital gains were never withheld, so realized gains are owed on top --
    the realistic way to end up writing a check in April. The full itemized breakdown is
    kept on state._tax so the UI can show every step of the math.
    """
    if state.turn % 12 != 0:
        return None

    bd = tax_breakdown(state.annual_gross_ytd, state.withheld_income_tax_ytd)
    reconciliation = bd["reconciliation"]
    cap_gains = state.capital_gains_owed

    refund = -reconciliation if reconciliation < 0 else 0
    state.cash += refund                                  # over-withheld -> money back

    tax_bill = max(0, reconciliation) + cap_gains
    state.tax_owed += tax_bill
    pay = min(state.cash, state.tax_owed)
    state.cash -= pay
    state.tax_owed -= pay

    state.withheld_income_tax_ytd = 0
    state.annual_gross_ytd = 0
    state.capital_gains_owed = 0

    state._tax = {**bd, "capital_gains": cap_gains, "refund": refund,
                  "tax_bill": tax_bill, "paid": pay, "still_owed": state.tax_owed}
    return state._tax


def phase_life_event(state, rng, forced: dict | None = None) -> dict | None:
    """Roll and apply one life event. `forced={'key','amount'}` scripts it for tests.

    Turn 1 is a grace month: no random event fires, so a new game never opens by
    slapping the player with a surprise bill. (Forced events still run, for tests.)
    """
    if forced is not None:
        bucket, amount = _bucket_by_key(forced["key"]), forced.get("amount")
    else:
        if state.turn <= 1:
            return None
        bucket, amount = rng.roll_bucket(config.EVENTS), None

    key = bucket["key"]
    desc = {"key": key, "label": _label_for(key, state.turn),
            "cash_delta": 0, "happiness_delta": 0,
            "gross_mult": bucket.get("gross_mult"), "layoff": bool(bucket.get("set_unemployed"))}

    if "happiness_range" in bucket:
        lo, hi = bucket["happiness_range"]
        swing = amount if amount is not None else rng.draw_int(lo, hi)
        state.event_happiness_delta = swing
        desc["happiness_delta"] = swing
    else:
        lo, hi = bucket["magnitude"]
        mag = amount if amount is not None else rng.draw_int(lo, hi)
        delta = bucket["sign"] * mag
        gap = max(0, -delta - state.cash)               # the part cash can't cover
        state.cash = max(0, state.cash + delta)
        if gap > 0:                                     # surprises don't evaporate: the
            _ensure_credit_card(state)["principal"] += gap   # unpaid part becomes card debt
        desc["cash_delta"] = delta
        desc["gap"] = gap
        if bucket.get("gross_mult") is not None:
            state.gross_month = round_half_up(state.gross_month * bucket["gross_mult"])
        if bucket.get("set_unemployed"):
            state.employed = False

    state._event = desc
    return desc
