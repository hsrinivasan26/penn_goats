"""The curriculum-alignment fixes: progressive taxes, event overflow, crypto crashes."""

import config
from game.state import new_game
from game.rng import SeededRNG
from game.formulas import federal_tax, tax_breakdown
from game.events import phase_life_event, phase_annual_tax
from game.economy import phase_markets
from game.engine import run_turn
from game.enums import DebtKind, AssetClass


# ---- progressive tax math (worked to the dollar) ---------------------------

def test_federal_tax_brackets():
    assert federal_tax(0) == 0
    assert federal_tax(12_000) == 1_200                       # all in the 10% bracket
    assert federal_tax(24_600) == 1_200 + round(12_600 * 0.12)  # path A's first year
    assert federal_tax(60_600) == 1_200 + 4_320 + round(12_600 * 0.22)  # junior SWE year


def test_wage_earners_over_withhold_and_get_refunds():
    # Path A start: $3,300/mo -> $39,600/yr, withheld flat 15% = $5,940.
    bd = tax_breakdown(39_600, 5_940)
    assert bd["taxable"] == 24_600
    assert bd["liability"] == bd["federal"] + bd["state"]
    assert bd["reconciliation"] < 0                           # refund, like most wage-earners


def test_refund_is_actually_paid_into_cash():
    s = new_game("A", seed=1)
    s.turn = 12
    s.annual_gross_ytd = 39_600
    s.withheld_income_tax_ytd = 5_940
    cash0 = s.cash
    t = phase_annual_tax(s)
    assert t["refund"] > 0 and s.cash == cash0 + t["refund"]
    assert t["gross"] == 39_600 and t["deduction"] == config.STD_DEDUCTION


def test_capital_gains_still_create_a_bill():
    s = new_game("A", seed=1)
    s.turn = 12
    s.annual_gross_ytd = 39_600
    s.withheld_income_tax_ytd = 5_940
    s.capital_gains_owed = 10_000                             # big realized gains
    t = phase_annual_tax(s)
    assert t["capital_gains"] == 10_000
    assert t["tax_bill"] == 10_000                            # wages refunded, gains owed


# ---- surprise costs overflow to the credit card ----------------------------

def test_event_bigger_than_cash_goes_on_the_card():
    s = new_game("A", seed=1)                                 # $500 cash
    desc = phase_life_event(s, SeededRNG(0), forced={"key": "mod_neg", "amount": 2_000})
    assert s.cash == 0
    assert desc["gap"] == 1_500
    assert s.liabilities[DebtKind.CREDIT_CARD]["principal"] == 1_500


def test_event_within_cash_creates_no_gap():
    s = new_game("A", seed=1)
    desc = phase_life_event(s, SeededRNG(0), forced={"key": "small_neg", "amount": 200})
    assert desc["gap"] == 0
    assert s.liabilities[DebtKind.CREDIT_CARD] is None


# ---- crypto crashes --------------------------------------------------------

class _CrashRNG:
    """draw_normal -> calm; draw_int(1,10000) -> 1 (crash fires); crash size -> lower bound."""
    def draw_normal(self, mu, sigma):
        return mu
    def draw_int(self, lo, hi):
        return 1 if (lo, hi) == (1, 10_000) else lo


def test_crypto_crash_fires_and_is_visible():
    s = new_game("A", seed=1)
    s.investments[AssetClass.CRYPTO] = 10_000
    applied = phase_markets(s, _CrashRNG())
    assert applied["crypto"] == config.RETURNS["crypto"]["crash_range"][0]  # -60%
    assert s.investments[AssetClass.CRYPTO] == 4_000


def test_non_crypto_assets_never_crash():
    s = new_game("A", seed=1)
    s.investments[AssetClass.INDEX] = 10_000
    applied = phase_markets(s, _CrashRNG())
    assert applied["index"] == config.RETURNS["index"]["mu"]  # plain normal draw


def test_crash_rate_is_about_right_over_many_months():
    rng = SeededRNG(11)
    s = new_game("A", seed=11)
    crashes = 0
    for _ in range(1_000):
        s.investments[AssetClass.CRYPTO] = 10_000             # reset so it can't hit 0
        r = phase_markets(s, rng)["crypto"]
        if r <= -0.35:
            crashes += 1
    assert 15 <= crashes <= 70                                # ~4% of 1,000, loosely


# ---- milestones scale with the player's own economy ------------------------

def test_milestones_use_relative_thresholds():
    from game.engine import check_milestones, MILESTONES
    ids = {m["id"] for m in MILESTONES}
    assert {"one_month", "buffer", "quarter", "halfway"} <= ids

    s = new_game("A", seed=1)           # essentials: 1200+400+240+160 = 2000/mo rent path
    s.cash = 2_000
    check_milestones(s)                 # fires at most one per turn -> walk until stable
    fired = set(s.milestones_fired)
    assert "first_500" in fired or "one_month" in fired

    # one month of essentials == $2,000 exactly, not the old hardcoded $1,850
    s2 = new_game("A", seed=1)
    s2.cash = 1_900
    for _ in range(6):
        check_milestones(s2)
    assert "one_month" not in s2.milestones_fired
    s2.cash = 2_000
    for _ in range(6):
        check_milestones(s2)
    assert "one_month" in s2.milestones_fired


def test_halfway_milestone_tracks_the_actual_target():
    from game.engine import check_milestones
    s = new_game("A", seed=1)
    s.cash = int(0.5 * s.target) - 1_000
    for _ in range(10):
        check_milestones(s)
    assert "halfway" not in s.milestones_fired
    s.cash = int(0.5 * s.target) + 1_000
    for _ in range(10):
        check_milestones(s)
    assert "halfway" in s.milestones_fired


# ---- exponential happiness decay -------------------------------------------

def test_happiness_decay_scales_with_happiness():
    from game.happiness import phase_happiness
    for start, expected_decay in ((50, 5), (80, 8), (100, 10), (20, 3)):  # 20 -> floor 3
        s = new_game("A", seed=1)
        s.happiness = start
        phase_happiness(s)
        assert s.happiness == start - expected_decay, f"start {start}"


def test_neglect_still_reaches_burnout():
    from game.happiness import phase_happiness
    from game.enums import GameOver
    s = new_game("A", seed=1)                     # starts at 50, no leisure ever
    months = 0
    while s.game_over is None and months < 40:
        phase_happiness(s)
        months += 1
    assert s.game_over == GameOver.BURNOUT
    assert months <= 25                           # the floor keeps zero reachable
