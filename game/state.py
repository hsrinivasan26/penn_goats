# @dataclass(slots=True), which means the set of attributes is fixed.
# Prevents fatal type-safety bugs


from dataclasses import dataclass, field
import config
from .enums import GameOver, AssetClass, DebtKind, Housing

ASSET_CLASSES = list(AssetClass)                                    # order preserved for RNG reproducibility
DEBT_SLOTS = [DebtKind.STUDENT, DebtKind.MORTGAGE, DebtKind.CREDIT_CARD]


def _zero_assets() -> dict:
    return {c: 0 for c in ASSET_CLASSES}


def _empty_debts() -> dict:
    return {s: None for s in DEBT_SLOTS}

# !!! Don't touch these constants !!!
@dataclass(slots=True)
class GameState:
    # meta
    turn: int = 1
    rng_seed: int = 0
    path: str = "A"
    target: int = config.TARGET                 # net worth needed to win (per-path)
    game_over: GameOver | None = None

    # balances
    cash: int = 0
    happiness: int = 0
    investments: dict = field(default_factory=_zero_assets)
    cost_basis: dict = field(default_factory=_zero_assets)
    liabilities: dict = field(default_factory=_empty_debts)
    tax_owed: int = 0

    # income / employment
    employed: bool = True
    gross_month: int = 0

    # housing
    housing: Housing = Housing.RENT
    rent: int = 0
    mortgage_payment: int = 0

    # essentials (monthly)
    food: int = 0
    transport: int = 0
    utilities: int = 0

    # per-turn scratch (reset every turn)
    shortfall_flag: bool = False
    leisure_spend: int = 0
    event_happiness_delta: int = 0
    milestone_bonus: int = 0
    _event: dict | None = None
    _milestone: dict | None = None
    _paystub: dict | None = None
    _tax: dict | None = None

    # annual tax accumulators (reset each year boundary)
    withheld_income_tax_ytd: int = 0
    annual_gross_ytd: int = 0
    capital_gains_owed: int = 0

    # progress
    consecutive_shortfalls: int = 0
    milestones_fired: list = field(default_factory=list)
    history: list = field(default_factory=list)

    # --- derived quantities: computed on demand, never stored ---
    def investments_total(self) -> int:
        return sum(self.investments.values())

    def liabilities_total(self) -> int:
        total = self.tax_owed
        for slot in DEBT_SLOTS:
            liab = self.liabilities[slot]
            if liab is not None:
                total += liab["principal"]
        return total

    def net_worth(self) -> int:
        return self.cash + self.investments_total() - self.liabilities_total()

    # --- helpers ---
    def reset_scratch(self) -> None:
        """Clear this-turn-only fields at the start of every turn."""
        self.shortfall_flag = False
        self.leisure_spend = 0
        self.event_happiness_delta = 0
        self.milestone_bonus = 0
        self._event = None
        self._milestone = None
        self._paystub = None
        self._tax = None

    def validate(self) -> None:
        """Assert the spec invariants. Cheapest bug detector we have."""
        assert self.cash >= 0, f"cash negative: {self.cash}"
        assert 0 <= self.happiness <= 100, f"happiness out of range: {self.happiness}"
        for c in ASSET_CLASSES:
            assert self.investments[c] >= 0
            assert self.cost_basis[c] >= 0
        for slot in DEBT_SLOTS:
            liab = self.liabilities[slot]
            if liab is not None:
                assert liab["principal"] >= 0
        assert self.tax_owed >= 0

    def snapshot(self) -> dict:
        """A compact per-turn record for history / later charts."""
        return {
            "turn": self.turn,
            "cash": self.cash,
            "net_worth": self.net_worth(),
            "happiness": self.happiness,
            "employed": self.employed,
            "gross_month": self.gross_month,
            "shortfall": self.shortfall_flag,
            "event": None if self._event is None else self._event["label"],
        }


def new_game(path: str = "A", seed: int = 0) -> GameState:
    """Build a fresh GameState for starting scenario 'A' or 'B' (Phase 0 setup)."""
    cfg = config.PATHS[path]
    s = GameState(
        rng_seed=seed,
        path=path,
        target=cfg.get("target", config.TARGET),
        cash=cfg["cash"],
        happiness=config.HAPPINESS_START,
        gross_month=cfg["gross_month"],
        rent=config.ESSENTIALS["rent"],
        food=config.ESSENTIALS["food"],
        transport=config.ESSENTIALS["transport"],
        utilities=config.ESSENTIALS["utilities"],
    )
    loan = cfg["student_loan"]
    if loan is not None:
        s.liabilities[DebtKind.STUDENT] = {
            "principal": loan["principal"], "apr": loan["apr"], "kind": DebtKind.STUDENT,
        }
    return s
