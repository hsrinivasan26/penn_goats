"""Completion titles -- computed purely from a finished GameState (read-only).

A title is metadata (id, name, icon, blurb, kind) plus a rule(state) -> bool checked at
game-end. Kinds: 'win' (the goal), 'loss' (how a run ended), 'style' (how you played).
Nothing here writes to the engine, so titles can't disturb the team's game logic. A few
conditions are approximated from what state.history / balances currently record and can
tighten later if the engine starts tracking more (e.g. lifetime leisure spend).
"""

from game.enums import AssetClass, DebtKind, Housing


def _hist(s):
    return s.history or []


def _outcome(s):
    return s.game_over.value if s.game_over else None


def _student_cleared(s):
    liab = s.liabilities.get(DebtKind.STUDENT)
    return liab is None or liab["principal"] <= 0


TITLES = [
    {"id": "budget_goat", "name": "Budget GOAT", "icon": "🐐", "kind": "win",
     "blurb": "Reached your net-worth goal.",
     "rule": lambda s: _outcome(s) == "win"},
    {"id": "dug_out", "name": "Dug Out", "icon": "⛏️", "kind": "style",
     "blurb": "Won the graduate path — cleared the $30k loan.",
     "rule": lambda s: _outcome(s) == "win" and s.path == "B" and _student_cleared(s)},
    {"id": "airtight", "name": "Airtight", "icon": "🎯", "kind": "style",
     "blurb": "A whole game with zero shortfall months.",
     "rule": lambda s: len(_hist(s)) > 0 and not any(h["shortfall"] for h in _hist(s))},
    {"id": "loan_slayer", "name": "Loan Slayer", "icon": "🗡️", "kind": "style",
     "blurb": "Paid off your student loan in full.",
     "rule": lambda s: s.path == "B" and _student_cleared(s)},
    {"id": "homeowner", "name": "Homeowner", "icon": "🏠", "kind": "style",
     "blurb": "Bought your first house.",
     "rule": lambda s: s.housing == Housing.OWN},
    {"id": "diamond_hooves", "name": "Diamond Hooves", "icon": "💎", "kind": "style",
     "blurb": "Reached the goal with crypto in the mix.",
     "rule": lambda s: _outcome(s) == "win" and s.investments.get(AssetClass.CRYPTO, 0) > 0},
    {"id": "living_the_dream", "name": "Living the Dream", "icon": "☀️", "kind": "style",
     "blurb": "Ended with happiness 90+.",
     "rule": lambda s: s.happiness >= 90},
    {"id": "bounced_back", "name": "Bounced Back", "icon": "💼", "kind": "style",
     "blurb": "Survived a layoff and still hit the goal.",
     "rule": lambda s: _outcome(s) == "win" and any(not h["employed"] for h in _hist(s))},
    {"id": "overachiever", "name": "Overachiever", "icon": "🚀", "kind": "style",
     "blurb": "Won with net worth 25% past the goal.",
     "rule": lambda s: _outcome(s) == "win" and s.net_worth() >= s.target * 1.25},
    {"id": "mattress_stuffer", "name": "Mattress Stuffer", "icon": "🛏️", "kind": "style",
     "blurb": "Won without ever investing a dollar.",
     "rule": lambda s: _outcome(s) == "win" and s.investments_total() == 0 and sum(s.cost_basis.values()) == 0},
    {"id": "all_grind", "name": "All Grind, No Joy", "icon": "😤", "kind": "style",
     "blurb": "Finished with happiness under 25 the whole way.",
     "rule": lambda s: len(_hist(s)) >= 5 and all(h["happiness"] < 25 for h in _hist(s))},
    {"id": "miserably_rich", "name": "Miserably Rich", "icon": "💸", "kind": "style",
     "blurb": "Hit the goal but ended below 20 happiness.",
     "rule": lambda s: _outcome(s) == "win" and s.happiness < 20},
    {"id": "rug_pulled", "name": "Rug-Pulled", "icon": "🃏", "kind": "loss",
     "blurb": "Went bust holding crypto.",
     "rule": lambda s: _outcome(s) == "bankruptcy" and s.cost_basis.get(AssetClass.CRYPTO, 0) > 0},
    {"id": "ran_on_empty", "name": "Ran on Empty", "icon": "🔋", "kind": "loss",
     "blurb": "Burned out — happiness hit zero.",
     "rule": lambda s: _outcome(s) == "burnout"},
    {"id": "in_over_your_head", "name": "In Over Your Head", "icon": "🌊", "kind": "loss",
     "blurb": "Went bankrupt on a shortfall streak.",
     "rule": lambda s: _outcome(s) == "bankruptcy"},
    {"id": "treading_water", "name": "Treading Water", "icon": "🌀", "kind": "style",
     "blurb": "Survived all 60 months but missed the goal.",
     "rule": lambda s: _outcome(s) == "timeout"},
]


def earned_ids(state) -> set:
    """Ids of every title this finished game qualifies for (rules never raise)."""
    out = set()
    for t in TITLES:
        try:
            if t["rule"](state):
                out.add(t["id"])
        except Exception:
            pass
    return out


def by_id(tid):
    for t in TITLES:
        if t["id"] == tid:
            return t
    return None
