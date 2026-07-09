# Penn Goats — Financial Literacy Game (engine)

A pure-Python, terminal-runnable engine for the first-paycheck budgeting game.
No UI yet on purpose: we prove the *logic* is correct before building the
Streamlit skin. The engine is one state dict passed through eight phase
functions; the eventual UI will be a thin layer on top of exactly this.

## Run it

```bash
pip install -r requirements.txt      # just pytest

python play.py                       # play in the terminal (Path A, seed 0)
python play.py --path B --seed 7     # a different starting scenario / seed
python play.py --auto 60             # headless: auto-play 60 months, print a table

python -m pytest -q                  # run the verification suite
```

## Layout

```
config.py           every tunable number (difficulty lives here, nowhere else)
play.py             the terminal game loop
game/
  formulas.py       pure spec math (rounding, paystub, interest, gains, amortize…)
  enums.py          typo-safe constants: GameOver / AssetClass / DebtKind / Housing
  state.py          the GameState class (slots: a misspelled field raises) + new_game()
  rng.py            seeded randomness (same seed → same game → testable)
  paystub.py        Phase 1  income (gross→net)
  economy.py        Phases 2+3  markets + interest
  outflows.py       Phase 4  forced bill + shortfall
  events.py         Phase 5  year-end tax + one life event
  choices.py        Phase 6  the player's moves
  happiness.py      Phase 7  the anti-hoarding meter
  engine.py         Phase 8 checks + run_turn() (chains all 8) + milestones
data/
  events.json       life-event wording (content, no code)
  milestones.json   milestone bonuses (content, no code)
tests/
  test_worked_turn.py   the spec's worked examples, to the dollar
  test_invariants.py    invariants hold across many seeded games
  test_events.py        event probabilities + forced effects
```

## The turn (8 phases, in order)

income → markets → interest → forced outflows → events(tax + life) →
player choices → happiness → checks. `engine.run_turn()` is the one place that
runs this sequence; `play.py` and the tests both drive it, so they can't drift.

## Decisions & open items (please ratify as a team)

1. **BANKRUPTCY reworked (resolved).** The spec's `net_worth <= 0` loss rule made
   Path B lose on turn 1 (student debt = negative net worth from the start).
   Fixed: you now go bankrupt after `BANKRUPTCY_SHORTFALL_STREAK` months (default 3,
   in config.py) of failing to cover essentials — a cash-flow failure, which is
   what bankruptcy actually is. Net worth is now the *win* metric, not the lose
   metric, so Path B becomes the "dig out of student debt" arc. Win targets are now
   **per-path** and calibrated for equal difficulty (see Balance below).
2. **Mortgage amortizes.** Spec is silent on reducing mortgage principal, so a
   literal reading leaves it growing forever. `outflows.py` pays it down by the
   monthly payment. Doesn't affect the rent-based worked examples.
3. **Min payments capped at principal**, so a tiny balance can't be overpaid
   into a negative number (would break an invariant). Spec didn't cover it.
4. **Home asset = financed amount** (`price − down`), per the spec's explicit
   formula. Consequence: the down payment is a straight net-worth hit. Worth a
   second look if buying a home should feel better than that.
5. **Event/gross coupling.** Per the spec table, "moderate negative" always also
   cuts gross 10% and "large positive" always raises it 10%. If you'd rather
   split "medical bill" (cash only) from "hours cut" (gross only), that's a
   config/events change, no engine change.
6. **GoToSchool graduation effect** is unspecified — right now it just takes a
   student loan; whether/when finishing school raises gross is undecided.
7. **BuyCar on a loan** needs an `auto` debt slot (the state schema has only
   student/mortgage/credit_card). MVP does cash-only car purchases.
8. **Difficulty rebalanced (resolved).** The original economy was ~90% bankruptcy
   even under skilled play — see Balance below.

## Balance (how the two paths are made equally difficult)

Simulating 800 games/path showed the original config was near-unwinnable, from two
causes: (a) a **layoff** (`large_neg`) left you permanently unemployed with no way
back, and (b) Path A's monthly surplus was razor-thin. Fixes, all in `config.py`:

- A **"quiet month"** event bucket (30%) and rarer, gentler negatives.
- **Layoffs are now rare** (1%). They still make you unemployed — recover by taking
  a new job (the `change_job` action). *The eventual UI/coach should prompt this,
  or a laid-off beginner who doesn't job-hunt will lose.*
- Path A got a little relief both ways: gross $3000 → $3300 and essentials
  $2000 → $1850.
- **Per-path win targets**, calibrated so each path wins ~50% of the time under
  skilled play: Path A $23,000, Path B $68,000. They differ because Path B earns
  far more — a higher bar makes it *equally* hard, not easier.

Result (skilled vs reckless play): Path A 50% / 14% win, Path B 50% / 16% win. The
paths fail differently by design — Path A tends to go bankrupt (tight cash), Path B
tends to time out short of its higher target (comfortable but debt-burdened). Every
number here is a `config.py` knob; re-run `tests`/a sim after changing them.
