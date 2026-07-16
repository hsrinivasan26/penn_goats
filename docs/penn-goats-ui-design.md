# Penn Goats — UI Design

*The single home for UI/UX decisions: visual direction, the meter system, tooltips, and the screen map. The engine docs (spec, handoff, implementation-status) cover game logic; this doc covers what the player sees and touches. Working prototypes live in `ui/` (`prototype-rings.html` = The Month, `prototype-month-interactions.html` = its dialogs/coach, `prototype-screens.html` = Title/Choose/Results; `prototypes.html` = the early meter/layout study) — open them in a browser.*

**Status:** direction locked; all core screens designed. **Streamlit build started** — a playable vertical slice is live in `ui/` (`app.py` routing/screens, `render.py` HTML helpers, `style.py` CSS, `turn.py` interactive turn driver). Title → Choose → a full playable Month → basic Results all work (`streamlit run ui/app.py`). `turn.py` splits `run_turn` in two so the UI can pause for input — verified byte-identical to the engine across 80 games, but **keep it in sync if `run_turn` changes**. Still to port: modal action dialogs (currently tabs), the SVG results chart (currently `st.line_chart`), the coach line (static until the AI layer lands), and the Titles screen.

---

## 1. Direction & principles

A financial-literacy game for a **22-year-old intimidated by their first paycheck** — beginner-first, "you can do this," never "beat the leaderboard." Dark, calm, rounded. The one signature moment is the **gross→net paycheck reveal** (our teaching beat and our moat vs. lifetime-wealth sims); everything else stays quiet around it.

**Helpfulness rule (important).** UI text explains **how the game works** but never tells the player **what to do**. Three tiers of info: (1) *what the number is* — already on the meter, don't repeat it; (2) *its consequence or rule* — e.g. "0 = burnout", an APR, "below zero isn't a loss"; (3) *what you should do* — strategy. **Show tier 2, in one line, then stop.** Tier 3 is the coach's job (reactive, after the fact, in the player's own numbers) and is otherwise earned through consequences — the pedagogy is learning-by-doing (Fernandes: told lessons decay; Kaiser: active simulation sticks; Bertrand & Morse: a prompt *at* the decision moment), so a tooltip that spoils the answer undercuts the lesson *and* makes the game play itself. Going *below* tier 2 — hiding the rules or lose conditions — is **too far**; it reads as unfair, not as discovery. Litmus test: *does the label explain a mechanic/consequence, or give the answer?* The ⚠ about-to-lose warning is the one always-actionable exception (a safety signal).

## 2. Design tokens

**Palette (dark)**
| Token | Hex | Use |
|---|---|---|
| Background | `#0e1117` | app base |
| Surface | `#191c24` | cards / panels |
| Inset | `#12151c` | ring tracks, wells |
| Border | `#2a2f3a` | hairlines |
| Text / Muted | `#e8e8ea` / `#9aa0ac` | copy |
| **Brand purple** | `#8b6dff` | logo, primary buttons, progress accents |
| **Cash** | `#34d399` emerald | the Cash meter |
| **Investments** | `#f5b642` gold | the Investments meter (reads as "wealth") |
| **Debt** | `#ef4444` red | the Debt meter |
| **Happiness** | `#38bdf8` sky-blue → `#101b24` near-black | the Happiness meter — **color is dynamic**, bright sky when high, darkening as it drops |

**Type:** **Inter** throughout — headings, brand, and big numbers at heavier weights (600–700); labels and body copy at 400–500; tabular numerals for all money.

## 3. The four meters ("the four sliders")

**Form:** rings. **Placement:** a vertical rail, always visible, on the right side of the play screen (team decision). Each ring is hoverable.

**What each ring fills toward** (only Happiness has a natural 0–100, so the others need a scale — proposed, all tunable):
| Ring | Fills toward | Notes |
|---|---|---|
| Cash | ~3 months of essentials (a buffer) | immediate liquidity health |
| Investments | a nest-egg target (a fraction of the win goal) | long-term growth |
| Debt | a weighted debt-to-income "danger line" | uses `STRESS_WEIGHT`, so a credit-card balance fills/alarms the ring while an equal student loan stays calm |
| Happiness | value / 100 | color shifts sky-blue → black by value |

The Debt ring's alarm level reads `state.weighted_debt()` (already in the engine), which makes the good-debt/bad-debt lesson visual.

## 4. Tooltips

Hover any ring for a short, plain-language tooltip. Per the helpfulness rule (§1), tooltips **state the mechanic** — what the number is and how it moves — and don't hand over strategy. The **Cash tooltip is situation-aware** — three states, so it never shows a nonsensical "distance to goal" when the player is underwater:

1. **On track** (positive net worth, below goal): "$X of your $Y goal" + progress bar.
2. **Below zero · stable** (negative net worth, no active danger): reframes — student debt makes net worth negative and that's *normal, not game over*; keep covering essentials and it climbs.
3. **⚠ About to lose** (real lose-proximity — a **shortfall streak** heading toward bankruptcy, or happiness near burnout): a red warning with the concrete next action. Triggered off `consecutive_shortfalls` / `happiness`, **not** "debt > cash" — carrying student debt is normal and shouldn't cry wolf.

## 5. Screen map (the stages)

Four screens are certainly distinct. The beats inside "The Month" are pieces of that screen (modals/steps), not separate screens.

```
 [1 Title] → [2 Choose your start] → [3 THE MONTH  ↺ ~60×] → [4 Results] → (play again → 2)
                                         ├─ paycheck reveal (gross→net)
                                         ├─ the four rings (always visible)
                                         ├─ surprise event (pop-up)
                                         ├─ action dialogs (invest / sell / leisure / pay debt / big move)
                                         └─ end-of-month recap + AI coach line
```

**Core screens (all designed — see `prototype-screens.html` for 1/2/4, `prototype-rings.html` for 3):**
1. **Title / Start** — the goat, "Penn **Goats**", hook "From broke new hire to Budget GOAT," tag "A money game about your first real paychecks," a big **Start** + a quiet **How to play**. Purple-glow dark backdrop.
2. **Choose your start** — two path cards, framed as *lives* not difficulties (they're ~equal difficulty): **"Starting from scratch"** (no degree/debt, $3,300/mo, goal $23k) and **"Fresh graduate"** ($5,000/mo, $30k loan, goal $68k). Each shows Pay/Debt/Cash/Goal + a "Start this life" button. A line sets the expectation: "both winnable, about equally tough." (Name/avatar can slot in later.)
3. **The Month** — the core loop; the dashboard (rings rail + paycheck reveal + event + actions). Repeats until a win/lose condition. *Fully designed (see below).*
4. **Results / Game Over** — a headline (a win reads "Budget **GOAT**"; losses reuse the layout), a **net-worth-over-time chart** hand-drawn from `state.history` (the line runs red→gold→emerald→purple as you climb out of debt), final stats (net worth · goal · months · happiness), the coach's whole-run wrap-up, and **Play again** / **Main menu**.

**Inside The Month — designed** (see `prototype-month-interactions.html`):
- **Paycheck reveal** — the gross→net moment (the signature), center-stage on the dashboard.
- **Surprise event** — a centered pop-up (icon, label, cost, one neutral line, "Got it"). Fires before the player acts.
- **Action dialogs** — one shared modal pattern (title · available cash · inputs · Cancel/confirm). Each states **mechanics only** — strategy is left to consequences + the coach:
  - *Invest*: pick an asset (risk-free / index / growth / crypto, each with a neutral return + risk label) + amount; notes that buying isn't a net-worth loss and gains are taxed on sale.
  - *Pay debt*: pick a debt (shows its APR + minimum) + an extra amount. No "which first" advice — the APRs speak for themselves.
  - *Leisure*: amount + a live "+happiness" preview (the diminishing curve shows itself; no lecture).
  - *Big move*: a 2×2 menu (house / school / job / car), each expandable to its own inputs.
- **End-of-month recap + AI coach** — a ledger of the month (take-home, essentials, surprise, choices, cash now, happiness Δ) plus **one coach line in the player's own numbers**. This is the **home for strategy** — the "credit cards first" / "keep a buffer" nudges live here, reactive and personalized, not in the dialogs. The coach is the only place an LLM speaks and is grounded strictly in engine-computed figures (can't invent a number); a written recap is the fallback when no API key is set. "Next month ▶" advances.

**Retention screens — designed** (see `prototype-screens-extra.html`): **How to play** (5 steps + the four-ring legend; explains rules, not strategy) and **Titles / achievements** (below).

**Likely out of scope for this build:** the **leaderboard** — mocked (kept deliberately social, per the differentiation guide's warning against making it the motivator), but unlikely to ship in this timeline; and avatar/home **customization** (needs the mascot art + the coins/progression layer).

## 5b. Titles (completion achievements)

Earned from `state.history` at game-end, shown on Results ("Title earned: …") and collected on the Titles screen — a reason to replay in a different style, and a stealth teacher (earning "Loan Slayer" rewards good behaviour; "Miserably Rich" ribs you into caring about happiness). Tone: playful and a little self-roasting, but off clinical mental-health wording. **Content draft — becomes `data/titles.json` when built** (a title = id · name · icon · one-line condition · earned-from-state rule):

| Title | Earn condition |
|---|---|
| **Budget GOAT** 🐐 (win) | Reached your net-worth goal |
| **Dug Out** ⛏️ | Won the graduate path (cleared the $30k loan + hit goal) |
| **Airtight** 🎯 | A whole game with zero shortfall months |
| **Loan Slayer** 🗡️ | Paid off the student loan in full |
| **Homeowner** 🏠 | Bought a house |
| **Diamond Hooves** 💎 | Reached the goal with crypto in the portfolio |
| **Living the Dream** ☀️ | Ended with happiness 90+ |
| **Bounced Back** 💼 | Survived a layoff and still hit the goal |
| **Overachiever** 🚀 | Won with net worth well past the goal |
| **Mattress Stuffer** 🛏️ | Won without ever investing a dollar |
| **Treat Yourself** 🎉 | Spent big on leisure across the run |
| **All Grind, No Joy** 😤 | Finished with happiness under 25 the whole way |
| **Miserably Rich** 💸 | Hit the goal but ended below 20 happiness |
| **Rug-Pulled** 🃏 (loss) | Went bust after going heavy on crypto |
| **Ran on Empty** 🔋 (loss) | Burned out (happiness hit 0) |
| **In Over Your Head** 🌊 (loss) | Went bankrupt (shortfall streak) |
| **Treading Water** 🌀 | Survived all 60 months but missed the goal |

## 6. Stack & implementation

**Streamlit** over the pure-Python engine (keeps the engine the single source of truth; free deploy). The rings, tooltips, and paycheck reveal are rendered as **custom HTML/CSS** (via `st.markdown` / `st.components`) so they look exactly like the prototypes rather than default widgets. Persistent game state lives in `st.session_state`. Dark theme is set in `ui/.streamlit/config.toml`.

## 7. Open questions

- Layout of The Month: dashboard vs. stepped vs. hybrid (prototypes built; leaning hybrid — meters always visible + a focused paycheck moment).
- Exact ring fill scales (§3) — tune once the screen is live.
- Whether Choose-your-start also does character naming/avatar in the MVP.
- Happiness color ramp exact stops.
