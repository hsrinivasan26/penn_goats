# Penn Goats — Implementation Status & Decision Log

*The single "what's true now" reference. The design-handoff and game-loop-spec capture the design and its rationale; this doc records what's actually built and every decision that changed the spec during the build. Last updated for engine v1.1.*

---

## Status at a glance

The **engine is done**: the full 8-phase turn loop is implemented in pure Python, playable in the terminal, and covered by **18 passing tests** (including the spec's worked examples verified to the dollar). It is the foundation everything else sits on.

**Built:** the turn engine, the paystub / economy / events / choices / happiness math, seeded reproducibility, per-turn invariant checks, a data-driven event and milestone system, per-path starting scenarios, a balanced difficulty curve, and a terminal game (`play.py`, interactive or `--auto` for balance-testing).

**Not built yet:** the Streamlit UI, the AI coach, streak/level/coins retention, and the leaderboard. These are the next steps, in roughly that order.

## How to run

From the repo root:

```
pip install -r requirements.txt      # just pytest
python play.py                       # play in the terminal (Path A)
python play.py --path B --auto 60    # headless: auto-play, print a table
python -m pytest -q                  # the test suite (expect 18 passed)
```

`README.md` has the same instructions plus the module map.

## File tree (as built)

```
config.py            every tunable number (the single source of truth)
play.py              terminal game loop
conftest.py          lets tests import the package from the repo root
game/                the ENGINE (pure Python, no UI)
  formulas.py        pure spec math (rounding, paystub, interest, gains, amortize)
  enums.py           GameOver / AssetClass / DebtKind / Housing  (typo-safe)
  state.py           the GameState class + new_game() + invariants
  rng.py             seeded randomness
  paystub.py         Phase 1  income
  economy.py         Phases 2+3  markets + interest
  outflows.py        Phase 4  forced bill + shortfall
  events.py          Phase 5  year-end tax + one life event
  choices.py         Phase 6  player moves
  happiness.py       Phase 7  anti-hoarding meter
  engine.py          Phase 8 checks + run_turn() + milestones
data/
  events.json        life-event wording (content, no code)
  milestones.json    milestone bonuses (content, no code)
tests/               worked examples · invariants · events · enums
docs/                these design docs
```

Python-only teammates work entirely in `config.py` (numbers) and `data/*.json` (wording). Everyone runs one turn the same way: `engine.run_turn()` chains the eight phases; `play.py` and the tests both drive that one function, so they can't drift apart.

## Two safety decisions worth knowing

**State is a class, not a dict.** `GameState` is a `@dataclass(slots=True)`, which fixes the set of fields — so a misspelled write like `state.cahs = 100` raises `AttributeError` on the spot instead of silently creating a junk field that breaks something unrelated later. With a team still learning Python, that trade (a bit more ceremony for loud, immediate errors) is worth it. Access is `state.cash`, never `state["cash"]`.

**Enums for the values that must never be typos.** `GameOver`, `AssetClass`, `DebtKind`, and `Housing` are `(str, Enum)` classes: their members *are* strings, so they drop into dict keys and JSON unchanged, but `GameOver.BANKRUPCY` (typo) errors instead of becoming a dead string. One caveat: `str(GameOver.WIN)` prints `"GameOver.WIN"`, so any user-facing text uses `.value` (`"win"`). Event and milestone keys stay plain strings because their source of truth is a JSON file — an enum in code can't catch a typo there; a load-time check would.

## The turn (unchanged in shape from the spec)

income → markets → interest → forced outflows → events (tax + life) → player choices → happiness → checks. Every money calculation rounds half-up to whole dollars, and randomness is seeded, so a given seed reproduces an identical game — which is what makes the worked examples testable.

## Changelog — what changed from the design docs

| Area | Design docs said | Built (v1.1) | Why |
|---|---|---|---|
| **Bankruptcy** | `net_worth <= 0` | 3 consecutive shortfall months (`BANKRUPTCY_SHORTFALL_STREAK`) | The old rule made Path B lose on turn 1 (student debt = negative net worth). Bankruptcy is really a cash-flow failure; negative net worth from student loans is normal. |
| **Net worth** | the lose metric | the **win** metric | Lets Path B be the "dig out of debt" arc instead of an instant loss. |
| **Win target** | single `TARGET` = $25k | **per-path**: A $23k, B $68k | Calibrated so both paths win ~50% under skilled play — equal *difficulty*, not equal number. |
| **Events** | fire every turn, ~60% negative | added a 30% "quiet month"; layoffs rare (1%); gentler negatives | The original was ~90% bankruptcy even played well. |
| **Layoffs** | permanent (no recovery in spec) | still permanent but **rare**; recover via `ChangeJob` | Kept as a real stakes event; made rare because recovery is manual. |
| **Path A economy** | gross 3000, essentials 2000 | gross 3300, essentials 1850 | Path A's surplus was too thin to ever build a buffer. |
| **State** | a dict | a slotted `GameState` class | Typo-safety for a beginner team. |
| **Constants** | `PARAMS` dict | flat `config.py` constants + a `formulas.py` module | Cleaner for a non-coder to edit; formulas isolated and testable. |
| **Milestones** | inline (`+5` on BuyHouse) | data-driven `data/milestones.json` | Content-editable without touching code. |
| **Module `progression.py`** | in the sketch | deferred | Streak/level/coins is a retention layer for later; the engine ships the financial core. |
| **Debt stress weight** *(v1.1.1)* | all debt equal | per-kind `STRESS_WEIGHT` (credit_card 1.5 … student 0.15) | Teaches good-debt vs bad-debt: student/mortgage barely stress you, credit cards weigh heavy. Feeds stress→burnout only, never a direct loss. `STRESS_LIMIT` lowered 1.0→0.35 to match. Skilled win rate unchanged. |

Smaller build-time decisions where the spec was silent: the **mortgage principal now amortizes** (paying it down each month; otherwise it grew forever); **minimum debt payments are capped at the balance** (so a tiny balance can't be overpaid negative); the **home asset is booked at the financed amount** (`price − down`, per the spec's formula — a consequence is that the down payment is a straight net-worth hit).

## Balance — how the two paths are made equally difficult

800-game Monte-Carlo simulations drove the tuning. The headline: the original config was near-unwinnable (~90% bankruptcy under skilled play), dominated by **permanent layoffs** (a ~70% chance of getting laid off at least once over 60 months, with no way back = a death spiral) and by **Path A's razor-thin surplus**.

After the fixes above, under a skilled strategy (find a new job after a layoff, keep a buffer, kill credit-card debt first, invest the surplus):

| Path | Win target | Skilled win | Reckless win | Dominant failure |
|---|---|---|---|---|
| A (low income, no debt) | $23,000 | ~50% | ~14% | bankruptcy (tight cash) |
| B (higher income, $30k debt) | $68,000 | ~50% | ~16% | timeout short of the higher target |

Both paths win ~50% with skill and ~15% without — equally difficult, genuinely winnable, and skill clearly matters. They *fail* differently by design, which fits their identities. Every number here is a `config.py` knob; re-run the tests / a sim after changing them.

## Open items still to decide

- **GoToSchool graduation effect** — finishing school doesn't yet raise gross; decide whether/when it should.
- **BuyCar on a loan** — needs an `auto` liability slot (the state has only student/mortgage/credit_card); MVP does cash-only car purchases.
- **Event/gross coupling** — "moderate negative" always also cuts gross 10% and "large positive" always raises it 10%; you may want to split e.g. "medical bill" (cash only) from "hours cut" (gross only). Pure `config.py`/`data` change.
- **Home purchase feel** — because the home asset is the financed amount, buying a home is a net-worth hit up front; revisit if that should feel better.

## What's next

1. **Streamlit UI** over the engine — a thin skin; the engine already returns everything the screen needs (paystub breakdown, event, status, outcome). Remember to prompt "find a new job" after a layoff.
2. **AI coach** — one API call per round that explains the player's own numbers in plain language (the engine computes the numbers; the AI only narrates them, so it can't invent a wrong figure).
3. **Retention layer** — streak / level / coins / customization, and the leaderboard (faked with static peer scores for the MVP).
4. **Playtesting** — the balance numbers above are from a simulated "skilled" player; real playtests may shift the event mix or the targets. All tunable in `config.py`.
