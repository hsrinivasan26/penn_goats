# Penn Goats — Game Loop Specification (v1.1)

*Authoritative spec for the turn engine. The code must match this document. Every calculation here is defined precisely enough to verify by hand; §7 gives worked examples that should become unit tests. This supersedes the informal logic tree — corrections applied during review are listed in §9.*

> **v1.1 — implementation update (reflects the built engine).** The engine is implemented, terminal-playable, and covered by 18 passing tests. A few things changed during the build and are folded into this spec below: **bankruptcy** is now a recurring-shortfall rule (not `net_worth <= 0`); **`TARGET` is per-path** (Path A $23k, Path B $68k) for equal difficulty; the **event table and essentials were rebalanced** because the original numbers were ~90% bankruptcy; and the **state is a slotted class**, not a bare dict. See `docs/implementation-status.md` for the full changelog, the real file tree, and what's not built yet (UI, AI coach).

---

## 1. Conventions

- **Turn = 1 in-game month.** A "year boundary" is any turn where `turn % 12 == 0` (turns 12, 24, …); the annual tax reconciliation runs there.
- **Money** is stored and displayed in **whole dollars**. Any fractional result (interest, returns, tax, happiness gain) is **rounded half-up to the nearest dollar** immediately after the operation that produced it. Happiness is a **whole integer**.
- **RNG is seeded** (per game / per daily-challenge date). All randomness — market returns, event rolls — draws from the seeded generator so a given seed reproduces the exact same game. *This is what makes the engine testable: fix the seed, assert exact outputs.*
- **Determinism:** every phase is a pure function `phase(state) -> state` (markets and events additionally consume the seeded RNG). No hidden global state.
- **Sign convention:** deltas are applied to the named slider. "Cash −" means `cash` decreases. Cash may never end a phase below 0 (see invariants).

---

## 2. Invariants (assert after every turn)

These must always hold. Encode them as assertions in a `validate(state)` function run at the end of each turn — they are your cheapest bug detector.

1. `cash >= 0`
2. `0 <= happiness <= 100`
3. `net_worth == cash + investments_total - liabilities_total`
4. Every asset balance `>= 0`; every liability principal `>= 0`.
5. `shortfall_flag` is a boolean that was set exactly once this turn (in Phase 4).
6. Game ends (and no further phases run) the instant a lose/win condition is met.

**Terminal conditions:** *(v1.1 — bankruptcy reworked; see §9)*
- **Lose — bankruptcy:** `consecutive_shortfalls >= BANKRUPTCY_SHORTFALL_STREAK` (default 3). Failing to cover essentials three months in a row — a cash-flow failure. **Negative net worth is NOT a loss** (starting adulthood with student debt is normal); net worth is the *win* metric only.
- **Lose — burnout:** `happiness <= 0`
- **Lose — timeout:** `turn == TURN_LIMIT` and `net_worth < TARGET` *(TARGET is per-path — see §4)*
- **Win:** `turn == TURN_LIMIT` and `net_worth >= TARGET`

Add an invariant: `consecutive_shortfalls` increments each turn `shortfall_flag` is true and resets to 0 on any covered month.

---

## 3. State schema

The entire game is this one object. Types shown; initial values set in Phase 0.

> **v1.1 — state is now a class, not a bare dict.** It's a `@dataclass(slots=True)`
> `GameState` (in `game/state.py`), so the set of fields is fixed and a misspelled
> attribute (`state.cahs = 100`) raises `AttributeError` instead of silently creating
> junk — important with a beginner team. Access is `state.cash`, not `state["cash"]`.
> `investments`/`cost_basis`/`liabilities` keys and `housing`/`game_over` values use
> the `(str, Enum)` types in `game/enums.py` (`AssetClass`, `DebtKind`, `Housing`,
> `GameOver`). **Fields added since v1.0:** `target` (per-path win goal),
> `consecutive_shortfalls` (bankruptcy counter), `milestones_fired` (list), and the
> presentation-only `_event` / `_milestone` / `_paystub` / `_tax`. The dict below is
> still an accurate field-by-field map.

```python
state = {
  # --- meta ---
  "turn": 1,                     # int, 1-based
  "rng_seed": 0,                 # int
  "game_over": None,             # None | "bankruptcy" | "burnout" | "timeout" | "win"

  # --- sliders / balances ---
  "cash": 0,                     # int dollars, always >= 0
  "happiness": 0,                # int 0..100
  "investments": {               # int dollars per class (current market value)
      "riskfree": 0, "index": 0, "growth": 0, "crypto": 0, "home": 0
  },
  "cost_basis": {                # int dollars invested (for capital-gains calc)
      "riskfree": 0, "index": 0, "growth": 0, "crypto": 0, "home": 0
  },
  "liabilities": {               # each: {principal:int, apr:float, kind:str}
      "student": None, "mortgage": None, "credit_card": None
  },
  "tax_owed": 0,                 # int, unpaid assessed tax (a liability)

  # --- income / employment ---
  "employed": True,
  "gross_month": 0,              # int dollars, monthly gross

  # --- housing ---
  "housing": "rent",             # "rent" | "own"
  "rent": 0,                     # int, monthly (if renting)
  "mortgage_payment": 0,         # int, monthly (if owning; set at purchase)

  # --- essentials (monthly) ---
  "food": 0, "transport": 0, "utilities": 0,

  # --- per-turn scratch (reset at start of each turn) ---
  "shortfall_flag": False,
  "leisure_spend": 0,            # set in Phase 6, consumed in Phase 7
  "event_happiness_delta": 0,    # set in Phase 5, consumed in Phase 7
  "milestone_bonus": 0,          # set when a milestone fires, consumed in Phase 7

  # --- annual tax accumulators (reset at year boundary) ---
  "withheld_income_tax_ytd": 0,  # federal+state withheld this year
  "annual_gross_ytd": 0,         # gross earned this year
  "capital_gains_owed": 0,       # accrued from sells this year

  # --- history (for trends / charts) ---
  "history": [],                 # list of per-turn snapshots
}
```

Derived quantities (never stored; always computed):
```
investments_total = sum(investments.values())          # includes home equity
liabilities_total = sum(L.principal for L in liabilities if L) + tax_owed
net_worth         = cash + investments_total - liabilities_total
```

---

## 4. Parameters (single source of truth — tune here, nowhere else)

Every "magic number" lives in this table. The code reads from a `PARAMS` dict; hand-verification reads from here.

**Game length & goal**
| Name | Value | Note |
|---|---|---|
| `TURN_LIMIT` | 60 | months (5 years). |
| `TARGET` (per-path, v1.1) | A: 23000 · B: 68000 | net-worth goal to win — calibrated so both paths win ~50% under skilled play. Stored per path (`PATHS[..]["target"]`); `config.TARGET` (25000) is only a fallback default. |
| `BANKRUPTCY_SHORTFALL_STREAK` (v1.1) | 3 | consecutive shortfall months that trigger bankruptcy. |

**Taxes / withholding (applied to gross)**
| Name | Value |
|---|---|
| `FEDERAL_RATE` | 0.12 |
| `STATE_RATE` | 0.03 |
| `FICA_RATE` | 0.0765 |
| `INCOME_TAX_RATE` | 0.15 (= federal+state; used for annual reconciliation) |
| `CAP_GAINS_RATE` | 0.15 |

Withholding per paycheck = `FEDERAL_RATE + STATE_RATE + FICA_RATE = 0.2265`. Net = `gross × 0.7735`.

**Monthly investment returns** (drawn per turn from Normal(μ, σ), then applied multiplicatively)
| Class | μ / month | σ / month |
|---|---|---|
| `riskfree` | +0.003 | 0.000 (deterministic) |
| `index` | +0.007 | 0.030 |
| `growth` | +0.012 | 0.080 |
| `crypto` | +0.020 | 0.250 |
| `home` | +0.003 | 0.010 |

**Debt APRs**
| Debt | APR | Monthly rate = APR/12 |
|---|---|---|
| `student` | 0.06 | 0.005 |
| `mortgage` | 0.065 | 0.0054167 |
| `credit_card` | 0.24 | 0.02 |
| `auto` (v1.1) | 0.09 | 0.0075 |  *(defined for BuyCar-on-loan, which is not built yet)*

**Debt minimum payments (per month, while principal > 0)**
| Debt | Minimum |
|---|---|
| `student` | `max(50, round(0.01 × principal))` |
| `credit_card` | `max(35, round(0.03 × principal))` |
| `mortgage` | its `mortgage_payment` (counted in essentials, not here) |

**Essentials defaults (monthly)** *(v1.1 — trimmed from a $2000 baseline so Path A can survive)*
| Item | Value (v1.1) | was |
|---|---|---|
| `rent` (if renting) | 1100 | 1200 |
| `food` | 380 | 400 |
| `transport` | 230 | 250 |
| `utilities` | 140 | 150 |

**Happiness**
| Name | Value |
|---|---|
| `DECAY` | 4 (per turn, always) |
| `GAIN_SCALE` | 1.5 → `leisure_gain = round(1.5 × sqrt(leisure_spend))` |
| `STRESS_LIMIT` | 0.35 *(v1.1.1; was 1.0)* — **weighted**-debt-to-annual-gross ratio above which stress applies |
| `STRESS_PENALTY` | 5 |
| `SHORTFALL_PENALTY` | 15 |
| `happiness_start` | 60 |
| `STRESS_WEIGHT` *(v1.1.1)* | per-debt-kind stress weight: `credit_card` 1.5 · `tax` 1.2 · `auto` 0.8 · `mortgage` 0.10 · `student` 0.15 |

*(v1.1.1) Debt now weighs on stress by **kind**, not just size — "good debt" (student, mortgage) is light, credit cards are heavy. Phase 7 uses `weighted_debt = Σ principal × STRESS_WEIGHT[kind] (+ tax_owed × STRESS_WEIGHT["tax"])` instead of raw `liabilities_total`. This only feeds the stress→burnout channel; it never triggers a loss on its own.*

**Event table** (exactly one bucket fires per turn; probabilities sum to 100%) *(v1.1 — rebalanced; original was ~90% bankruptcy)*
| Bucket | Prob (v1.1) | was | Magnitude | Effect |
|---|---|---|---|---|
| **Quiet month (nothing happens)** | 30% | — | — | none |
| Small negative (car repair, dentist) | 22% | 35% | Small $ | Cash − |
| Moderate negative (medical bill, hours cut) | 8% | 20% | Medium $ | Cash − , Gross − (durable) |
| Large negative (**layoff — now rare**) | 1% | 5% | Large $ | Cash −− , sets `employed = False` |
| Small positive (bonus, refund) | 22% | 22% | Small $ | Cash + |
| Large positive (windfall, raise) | 3% | 3% | Large $ | Cash ++ (raise → Gross +) |
| Mood-only | 14% | 15% | N/A | Happiness ± |

Magnitudes (uniform int in range): `Small` = [50, 300], `Medium` = [300, 700] *(was 800)*, `Large` = [800, 2000] *(was 3000)*. Mood-only happiness delta = uniform int [−10, +10]. `Gross −` durable = reduce `gross_month` by 10%.

**Layoff recovery (v1.1):** a layoff still sets `employed = False` with no automatic recovery — the player gets back on their feet by taking a new job via the `ChangeJob` action (Phase 6). Layoffs were made rare (1%) precisely because recovery is manual; a UI/coach should prompt "find a new job" after one, or a beginner who doesn't will spiral.

**Path A / B setup** *(v1.1: Path A gross bumped; per-path targets added)*
| Field | Path A (low pay, no debt) | Path B (high pay, debt) |
|---|---|---|
| `gross_month` | 3300 (~40k/yr) *(was 3000)* | 5000 (60k/yr) |
| `student` loan | none | `{principal:30000, apr:0.06}` |
| `cash` start | 500 | 500 |
| `target` (win goal, v1.1) | 23000 | 68000 |
| everything else | defaults above | defaults above |

---

## 5. Turn sequence — exact operations

Each turn runs Phases 1–8 in order. Phase 0 runs once at game start. At the **start of every turn**, reset scratch: `shortfall_flag=False; leisure_spend=0; event_happiness_delta=0; milestone_bonus=0`.

### Phase 0 — Setup (once)
Choose path → apply the Path A/B row from §4 (including its per-path `target`, v1.1). Set `happiness = happiness_start`, `turn = 1`, `consecutive_shortfalls = 0`, seed RNG. Housing starts as `"rent"` with `rent = 1100` (v1.1).

### Phase 1 — Income
```
if not employed:
    net = 0
else:
    gross    = gross_month
    federal  = round(gross × FEDERAL_RATE)
    state_t  = round(gross × STATE_RATE)
    fica     = round(gross × FICA_RATE)
    net      = gross − federal − state_t − fica
    cash    += net
    withheld_income_tax_ytd += (federal + state_t)   # FICA is not reconciled
    annual_gross_ytd        += gross
# UI: display the four line items — this is the teaching moment.
```

### Phase 2 — Markets (unrealized)
```
for cls in ["riskfree","index","growth","crypto","home"]:
    if investments[cls] > 0:
        r = draw_normal(mu[cls], sigma[cls])          # seeded
        investments[cls] = max(0, round(investments[cls] × (1 + r)))
# Cash is NOT touched. Gains/losses are unrealized until a sell in Phase 6.
```

### Phase 3 — Interest (liabilities grow only)
```
for L in [student, mortgage, credit_card] if present:
    L.principal += round(L.principal × (L.apr / 12))
# No cash movement here. Cash is drained in Phase 4.
```

### Phase 4 — Forced outflows (the teaching phase)
```
housing_cost   = mortgage_payment if housing == "own" else rent
essentials     = housing_cost + food + transport + utilities
debt_minimums  = student_min + credit_card_min          # NOT mortgage (already in essentials)
REQUIRED_OUTFLOW = essentials + debt_minimums

if cash >= REQUIRED_OUTFLOW:
    cash -= REQUIRED_OUTFLOW
    apply debt_minimums to their principals (reduce each)
    shortfall_flag = False
else:
    shortfall_flag = True
    gap  = REQUIRED_OUTFLOW − cash        # CORRECTED sign (positive amount still owed)
    cash = 0                              # spend everything available
    credit_card.principal += gap          # unpaid remainder becomes high-interest debt
    # (create credit_card liability if none exists)
```
*Note: essentials always get "covered"; when short, the coverage is forced borrowing at credit-card APR — that is the consequence the game teaches. The two review-flagged bullets ("add rest to liabilities" / "charge gap to credit card") are the same single operation above.*

*(v1.1) Immediately after this phase, update the bankruptcy counter: `consecutive_shortfalls = consecutive_shortfalls + 1 if shortfall_flag else 0`. When owning, the `mortgage_payment` (inside essentials) also pays down the mortgage principal — the spec was silent on this, and without it the loan would grow forever. Debt minimums are capped at the remaining principal so a tiny balance can't be overpaid negative.*

### Phase 5 — Events
**5a. Annual tax (only if `turn % 12 == 0`):**
```
actual_income_tax = round(annual_gross_ytd × INCOME_TAX_RATE)
reconciliation    = actual_income_tax − withheld_income_tax_ytd   # +owe / −refund
tax_bill          = max(0, reconciliation) + capital_gains_owed
tax_owed         += tax_bill
pay = min(cash, tax_owed); cash -= pay; tax_owed -= pay           # pay what you can
# reset accumulators:
withheld_income_tax_ytd = 0; annual_gross_ytd = 0; capital_gains_owed = 0
```

**5b. Life event (every turn):** roll one bucket by cumulative probability from the §4 table; draw magnitude; apply:
```
Cash effects:  cash = max(0, cash + delta)      # negative events can't push cash below 0;
                                                # any uncovered remainder is simply lost value this turn
Gross − :      gross_month = round(gross_month × 0.90)   (durable)
Layoff:        employed = False
Raise (Gross +): gross_month = round(gross_month × 1.10) (durable)
Mood-only:     event_happiness_delta = draw_int(-10, +10)   # consumed in Phase 7
```

### Phase 6 — Player choices (with leftover cash)
Each action validated against its precondition; reject (no-op) if violated.
```
Invest(amount, cls):   require 0 < amount <= cash
                       cash -= amount; investments[cls] += amount; cost_basis[cls] += amount

Sell(amount, cls):     require 0 < amount <= investments[cls]
                       frac  = amount / investments[cls]
                       basis = round(cost_basis[cls] × frac)
                       gain  = amount − basis
                       investments[cls] -= amount; cost_basis[cls] -= basis; cash += amount
                       if gain > 0: capital_gains_owed += round(gain × CAP_GAINS_RATE)

Leisure(amount):       require 0 < amount <= cash
                       cash -= amount; leisure_spend += amount      # happiness applied in Phase 7

PayDebt(amount, L):    require 0 < amount <= min(cash, L.principal)
                       cash -= amount; L.principal -= amount
```
**Big moves** (each may fire a `milestone_bonus`):
```
TakeLoan(P, apr, kind):    cash += P; create/extend liability {P, apr, kind}
GoToSchool(cost):          TakeLoan(cost, 0.06, "student"); (optionally raises future gross on "graduation")
BuyHouse(price, down):     require down <= cash
                           cash -= down; housing = "own"
                           mortgage = {principal: price − down, apr: 0.065}
                           mortgage_payment = amortize(price − down, 0.065/12, 360)
                           investments["home"] += (price − down); cost_basis["home"] += (price − down)
                           milestone_bonus += 5
ChangeJob(new_gross):      gross_month = new_gross; employed = True
BuyCar(price):             either Cash − price, or TakeLoan(price, apr, "auto")
```
`amortize(P, i, n) = round(P × i × (1+i)^n / ((1+i)^n − 1))`.

### Phase 7 — Happiness
```
h  = happiness
h -= DECAY
debt_ratio = weighted_debt / max(1, gross_month × 12)   # v1.1.1: weighted by debt kind, not raw total
if debt_ratio > STRESS_LIMIT:  h -= STRESS_PENALTY
if shortfall_flag:             h -= SHORTFALL_PENALTY
h += round(GAIN_SCALE × sqrt(leisure_spend))
h += event_happiness_delta + milestone_bonus
happiness = clamp(round(h), 0, 100)
if happiness <= 0:  game_over = "burnout"; STOP
```

### Phase 8 — Checks  *(v1.1 — bankruptcy rule replaced)*
```
if consecutive_shortfalls >= BANKRUPTCY_SHORTFALL_STREAK:   game_over = "bankruptcy"; STOP
elif turn == TURN_LIMIT:
    game_over = "win" if net_worth >= target else "timeout"; STOP   # target is per-path
append snapshot to history
turn += 1
```
*Was `if net_worth <= 0: bankruptcy`. That made Path B (which starts ~−$29.5k from student debt) lose on turn 1, so bankruptcy is now a cash-flow failure (recurring shortfalls) and net worth is only the **win** metric. `target` comes from the chosen path.*

---

## 6. Consolidated formula reference

| Quantity | Formula |
|---|---|
| Net pay | `gross − round(gross·0.12) − round(gross·0.03) − round(gross·0.0765)` |
| Investment value | `round(balance · (1 + r))`, `r ~ Normal(μ, σ)` |
| Interest accrual | `principal += round(principal · APR/12)` |
| Required outflow | `housing + food + transport + utilities + student_min + cc_min` |
| Shortfall gap | `REQUIRED_OUTFLOW − cash` (only when cash < outflow) |
| Capital gain on sale | `amount_sold − round(cost_basis · amount_sold/balance)` |
| Cap-gains tax | `round(gain · 0.15)` if gain > 0 |
| Annual reconciliation | `round(annual_gross · 0.15) − withheld_ytd` |
| Leisure happiness | `round(1.5 · sqrt(leisure_spend))` |
| Net worth | `cash + Σ investments − (Σ liability principals + tax_owed)` |

---

## 7. Worked examples (turn these into unit tests)

### Example 1 — Path A, Turn 1, normal (cash ≥ outflow)
**Start:** `cash=500, happiness=60, gross_month=3000, employed, renting, no debt/investments.`
Assume fixed rolls: life event = **Small negative, $150**; player then spends **$100 leisure** and **invests $200 index**.

| Phase | Operation | Result |
|---|---|---|
| 1 | federal 360, state 90, fica 230 → net = 3000−680 = **2320**; cash 500+2320 | `cash = 2820`; `withheld_ytd = 450`; `annual_gross_ytd = 3000` |
| 2 | no investments owned | no change |
| 3 | no debt | no change |
| 4 | essentials = 1200+400+250+150 = **2000**; cash 2820 ≥ 2000 → cash 2820−2000 | `cash = 820`; `shortfall_flag = False` |
| 5 | turn 1, not year-end → no tax. Event small-neg $150 → cash 820−150 | `cash = 670` |
| 6 | Leisure 100 → cash 570, `leisure_spend=100`. Invest index 200 → cash 370, `index=200`, `basis.index=200` | `cash = 370` |
| 7 | h=60 −4 (decay) = 56; debt_ratio 0 → no stress; no shortfall; +round(1.5·√100)=+15 → 71; no mood/milestone | `happiness = 71` |
| 8 | investments_total=200; liabilities_total=0; net_worth = 370+200−0 = **570** ≥ 0; turn ≠ 60 | `net_worth = 570`; continue, `turn = 2` |

**Assert after Turn 1:** `cash==370, happiness==71, investments["index"]==200, net_worth==570, shortfall_flag==False`.

### Example 2 — the shortfall branch
**Start of Phase 4:** `cash=1500`, renting, no debt yet. `REQUIRED_OUTFLOW = 2000`.
```
cash 1500 < 2000 → shortfall_flag = True
gap = 2000 − 1500 = 500
cash = 0
credit_card.principal = 500        (created)
```
**Phase 7 effect:** `h -= SHORTFALL_PENALTY (15)`.
**Next turn, Phase 3:** `credit_card.principal += round(500 · 0.02) = 10 → 510`.
**Assert:** after this turn `cash==0, shortfall_flag==True, credit_card.principal==500`; after next turn's Phase 3 `credit_card.principal==510`.

### Example 3 — capital gains on a sell
`index balance = 400, cost_basis.index = 200`. Player sells `100`.
```
frac  = 100/400 = 0.25
basis = round(200 · 0.25) = 50
gain  = 100 − 50 = 50
capital_gains_owed += round(50 · 0.15) = 8
→ index 300, cost_basis.index 150, cash += 100, capital_gains_owed += 8
```

---

## 8. Edge cases & rules

- **Cash floor:** no action or event may drive `cash < 0`. Player actions are rejected if unaffordable; negative events clamp at 0 (uncovered value is lost, not borrowed — except Phase 4's forced credit borrowing, which is the one exception, by design).
- **Selling more than owned / paying more than owed:** reject (no-op).
- **Empty asset when computing `frac`:** guard `investments[cls] > 0` before dividing.
- **Rounding:** apply once, immediately after each arithmetic operation, half-up.
- **Milestones** (paid off a loan, bought a home, first $X saved) each set `milestone_bonus` once; fire at most one bonus per turn to avoid stacking.
- **Determinism:** the same `rng_seed` + the same player choices must reproduce identical state every turn. Tests depend on this.

---

## 9. Corrections applied (vs. the settled logic tree) & open items

**Corrections baked into this spec:**
1. ~~**Bankruptcy** is `net_worth <= 0`~~ → **superseded in v1.1**: bankruptcy is now a recurring-shortfall rule (see §2/§8). The `net_worth <= 0` version made Path B lose on turn 1.
2. **Shortfall gap** is `REQUIRED_OUTFLOW − cash` (tree had the sign reversed).
3. **Shortfall handling deduplicated** to one operation (unpaid remainder → credit card).
4. **Rent-hike event** raises essentials via a durable rent increase, *not* `Gross −`; `Gross −` is reserved for job events (hours cut, demotion).
5. **Housing fork resolved:** own → `mortgage_payment` in essentials + `home` as an appreciating asset; rent → flat `rent` in essentials, no asset.

**Open items — status (v1.1):**
- **Difficulty / event balance — RESOLVED.** 800-game simulations showed the original table was ~90% bankruptcy even under skilled play (the dominant cause was permanent layoffs). Fixed via a 30% "quiet month" bucket, rare (1%) layoffs, gentler negatives, and Path A relief. Both paths now win ~50% under skilled play. See `docs/implementation-status.md` → Balance.
- **Scope (`TURN_LIMIT` / `TARGET`) — RESOLVED.** Early-career confirmed (60 months). `TARGET` is now **per-path** ($23k A / $68k B) to make the two equally difficult.
- **Graduation effect of `GoToSchool` — still open.** `GoToSchool` currently just takes a student loan; whether/when finishing school raises gross is undecided.
- **New open items from the build:** home asset = financed amount (down payment is a straight net-worth hit); "moderate negative" always also cuts gross and "large positive" always raises it (could split); `BuyCar`-on-loan needs an `auto` liability slot (MVP is cash-only). All listed in `README.md` and `docs/implementation-status.md`.

---

*Implemented per this spec (v1.1). Phases 0–8 are live in `game/`, with §7's worked examples as passing tests. See `docs/implementation-status.md` for the current build state.*
