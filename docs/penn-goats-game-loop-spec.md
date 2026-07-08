# Penn Goats — Game Loop Specification (v1.0)

*Authoritative spec for the turn engine. The code must match this document. Every calculation here is defined precisely enough to verify by hand; §7 gives worked examples that should become unit tests. This supersedes the informal logic tree — corrections applied during review are listed in §9.*

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

**Terminal conditions:**
- **Lose — bankruptcy:** `net_worth <= 0`
- **Lose — burnout:** `happiness <= 0`
- **Lose — timeout:** `turn == TURN_LIMIT` and `net_worth < TARGET`
- **Win:** `turn == TURN_LIMIT` and `net_worth >= TARGET`

---

## 3. State schema

The entire game is this one object. Types shown; initial values set in Phase 0.

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
| `TURN_LIMIT` | 60 | months (5 years). Scope knob — see §9 note. |
| `TARGET` | 25000 | net-worth goal to win (early-career: a real buffer, not FIRE) |

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

**Debt minimum payments (per month, while principal > 0)**
| Debt | Minimum |
|---|---|
| `student` | `max(50, round(0.01 × principal))` |
| `credit_card` | `max(35, round(0.03 × principal))` |
| `mortgage` | its `mortgage_payment` (counted in essentials, not here) |

**Essentials defaults (monthly)**
| Item | Value |
|---|---|
| `rent` (if renting) | 1200 |
| `food` | 400 |
| `transport` | 250 |
| `utilities` | 150 |

**Happiness**
| Name | Value |
|---|---|
| `DECAY` | 4 (per turn, always) |
| `GAIN_SCALE` | 1.5 → `leisure_gain = round(1.5 × sqrt(leisure_spend))` |
| `STRESS_LIMIT` | 1.0 (debt-to-annual-gross ratio above which stress applies) |
| `STRESS_PENALTY` | 5 |
| `SHORTFALL_PENALTY` | 15 |
| `happiness_start` | 60 |

**Event table** (exactly one bucket fires per turn; probabilities sum to 100%)
| Bucket | Prob | Magnitude | Effect |
|---|---|---|---|
| Small negative (car repair, dentist) | 35% | Small $ | Cash − |
| Moderate negative (medical bill, hours cut) | 20% | Medium $ | Cash − , Gross − (durable) |
| Large negative (layoff) | 5% | Large $ | Cash −− , sets `employed = False` |
| Small positive (bonus, refund) | 22% | Small $ | Cash + |
| Large positive (windfall, raise) | 3% | Large $ | Cash ++ (raise → Gross +) |
| Mood-only | 15% | N/A | Happiness ± |

Magnitudes (uniform int in range): `Small` = [50, 300], `Medium` = [300, 800], `Large` = [800, 3000]. Mood-only happiness delta = uniform int [−10, +10]. `Gross −` durable = reduce `gross_month` by 10%.

**Path A / B setup**
| Field | Path A (low pay, no debt) | Path B (high pay, debt) |
|---|---|---|
| `gross_month` | 3000 (36k/yr) | 5000 (60k/yr) |
| `student` loan | none | `{principal:30000, apr:0.06}` |
| `cash` start | 500 | 500 |
| everything else | defaults above | defaults above |

---

## 5. Turn sequence — exact operations

Each turn runs Phases 1–8 in order. Phase 0 runs once at game start. At the **start of every turn**, reset scratch: `shortfall_flag=False; leisure_spend=0; event_happiness_delta=0; milestone_bonus=0`.

### Phase 0 — Setup (once)
Choose path → apply the Path A/B row from §4. Set `happiness = happiness_start`, `turn = 1`, seed RNG. Housing starts as `"rent"` with `rent = 1200`.

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
debt_ratio = liabilities_total / max(1, gross_month × 12)
if debt_ratio > STRESS_LIMIT:  h -= STRESS_PENALTY
if shortfall_flag:             h -= SHORTFALL_PENALTY
h += round(GAIN_SCALE × sqrt(leisure_spend))
h += event_happiness_delta + milestone_bonus
happiness = clamp(round(h), 0, 100)
if happiness <= 0:  game_over = "burnout"; STOP
```

### Phase 8 — Checks
```
if net_worth <= 0:                              game_over = "bankruptcy"; STOP   # CORRECTED (was = 0)
if turn == TURN_LIMIT:
    game_over = "win" if net_worth >= TARGET else "timeout"; STOP
append snapshot to history
turn += 1
```

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
1. **Bankruptcy** is `net_worth <= 0` (tree said `= 0`).
2. **Shortfall gap** is `REQUIRED_OUTFLOW − cash` (tree had the sign reversed).
3. **Shortfall handling deduplicated** to one operation (unpaid remainder → credit card).
4. **Rent-hike event** raises essentials via a durable rent increase, *not* `Gross −`; `Gross −` is reserved for job events (hours cut, demotion).
5. **Housing fork resolved:** own → `mortgage_payment` in essentials + `home` as an appreciating asset; rent → flat `rent` in essentials, no asset.

**Open items to settle (parameters, not structure):**
- **Difficulty / event balance.** As specified, an event fires every turn and ~60% are negative cash hits — combined with essentials + decay this may be punishing early. *Recommendation:* add a `Quiet (nothing happens)` bucket (~20%) and rescale, or make turns 1–3 event-free. This is a `PARAMS` change; the engine doesn't move.
- **Scope (`TURN_LIMIT` / `TARGET`).** Set to 60 months / $25k here, i.e., early-career. A lifetime arc means raising both — but that pushes the game toward the *Escape the Grind* shape (see differentiation guide). Decide deliberately; it's two numbers.
- **Graduation effect** of `GoToSchool` (does finishing school raise gross, and after how many turns?) — currently unspecified; define before implementing big moves.

---

*Once §4 numbers and the three open items are ratified, this spec is complete enough to implement Phases 0–8 directly, with §7 as the first unit tests.*
