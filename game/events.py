"""Phase 5: the year-end tax bill (5a) and exactly one life event per turn (5b).

Sizes/probabilities live in config.EVENTS; the wording lives in data/events.json.
"""

import json
import os
import config
from .formulas import round_half_up, annual_reconciliation

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
    """At a year boundary, reconcile withholding vs. tax owed, add capital gains, pay what cash allows."""
    if state.turn % 12 != 0:
        return None

    reconciliation = annual_reconciliation(state.annual_gross_ytd, state.withheld_income_tax_ytd)
    tax_bill = max(0, reconciliation) + state.capital_gains_owed

    state.tax_owed += tax_bill
    pay = min(state.cash, state.tax_owed)
    state.cash -= pay
    state.tax_owed -= pay

    state.withheld_income_tax_ytd = 0
    state.annual_gross_ytd = 0
    state.capital_gains_owed = 0

    state._tax = {"tax_bill": tax_bill, "reconciliation": reconciliation, "paid": pay,
                  "still_owed": state.tax_owed}
    return state._tax


def phase_life_event(state, rng, forced: dict | None = None) -> dict:
    """Roll and apply one life event. `forced={'key','amount'}` scripts it for tests."""
    if forced is not None:
        bucket, amount = _bucket_by_key(forced["key"]), forced.get("amount")
    else:
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
        state.cash = max(0, state.cash + delta)         # losses can't push cash below 0
        desc["cash_delta"] = delta
        if bucket.get("gross_mult") is not None:
            state.gross_month = round_half_up(state.gross_month * bucket["gross_mult"])
        if bucket.get("set_unemployed"):
            state.employed = False

    state._event = desc
    return desc
