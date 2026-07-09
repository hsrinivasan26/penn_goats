# Penn Goats — Financial Literacy Game
## Project Memory & Design Handoff

*A transfer document capturing the full design state so it can be handed to a teammate, revisited later, or pasted into a new working session. Read top to bottom to understand the whole project; jump to a section to answer a specific question.*

**Team:** Aicha Faye, Dylan Chen, Prisha Roy, Shiyu Huang, Jonathan Yang
**Course:** HME5354 (design course)
**Constraint:** ~4 weeks to build a minimum viable prototype (ugly/primitive is acceptable)
**One line:** A free browser game that teaches young adults how to plan around their first paychecks so they cover essentials without recurring shortfalls.

---

## 1. Need statement & specifications

**Locked need statement:**
> A way to address the difficulty of planning around first paychecks among young adults new to the workforce that results in reliably covering essential expenses without recurring shortfalls.

**Need criteria:** easily accessible · considers real-world circumstances · educates users effectively · adapts to and suggests consumer behavior.

**Need specifications (quantitative targets):**

| Criterion | Specification | Value |
|---|---|---|
| Easily accessible | No prior experience required | — |
| Easily accessible | Fees | **$0** |
| Real-world circumstances | Addresses likely volatility (inflation, market swings, unstable income) | — |
| Educates effectively | Engages the user | — |
| Educates effectively | Assesses info retention | **≥ 2 wks retention, ≤ 19% churn** |
| Consumer behavior | Behavioral analysis of saving/spending | — |
| Consumer behavior | Shifts strategy / gives suggestions | — |

---

## 2. Why this problem (the evidence grounding)

**The sharp insight the whole project rests on:** the problem is *not* a general deficit of financial literacy (diffuse, crowded, weak-evidence). It is a **specific, recurring miscalculation at a predictable moment** — new earners plan against *gross* pay (offer letter, hourly rate × hours) and are blindsided when taxes/deductions leave a smaller *net* deposit. The gap between the planned-against number and the deposited number is the proximate cause of shortfalls, overdrafts, and credit reliance.

**The highest-stakes instance:** signing a lease. The standard "spend 30% on housing" rule is calculated on *gross* income, which can push rent toward ~40% of real take-home — the threshold where credit-card reliance begins.

**Key supporting figures:**
- ~42% of Gen Z report living paycheck to paycheck (BofA 2026 Better Money Habits study).
- Family financial support is declining: 34% of Gen Z receive it, down from 46% in 2024 (same study).
- US credit card debt reached $1.25 trillion in Q1 2026 (NY Fed), with weakness concentrated in lower-income households.

**The evidence base for the *design approach* (this is why the game works the way it does):**
- **Fernandes, Lynch & Netemeyer (2014), *Management Science*:** generic financial education explains ~0.1% of variance in behavior and decays within ~20 months — but argues explicitly for **"just-in-time" education** tied to a decision moment.
- **Kaiser, Lusardi, Menkhoff & Urban (2022), *Journal of Financial Economics*:** meta-analysis of 76 RCTs — financial education *does* work when well-designed, and **active-learning/simulation designs** yield higher effects. (The counterweight to Fernandes.)
- **Bertrand & Morse (2011), *Journal of Finance*:** a single well-framed prompt at the decision moment, **in concrete dollars rather than percentages/APRs**, measurably changed behavior.
- **Drexler, Fischer & Schoar (2014), *AEJ: Applied*:** **simple rules-of-thumb beat a full curriculum**, with the largest benefit for the *least* financially experienced users — exactly the target population.

**Design DNA distilled:** just-in-time + concrete dollars + simple rules-of-thumb + learning-by-doing. The game is a vehicle for all four.

---

## 3. Solution decision

Chosen: **a free browser-based game** (Option 2). Considered and set aside: a bank-connected adaptive budgeting app (heavy build, privacy/fee friction), and a "pocket FP&A" purchase-decision companion (good idea, resource-heavy). The game won on feasibility in 4 weeks, $0/no-registration accessibility, and fit to the active-learning evidence.

---

## 4. Game concept

An **Oregon-Trail-style pixel life-sim** where the gameplay *is* the financial education. Home screen: the character + bio (job, house, mood, outfits reflecting their situation) + four performance sliders. Events arrive as pop-ups (AI-narrated, from a bounded rules-defined menu).

**Core loop (per turn / pay cycle):**
1. A paycheck arrives; the player opens a **realistic paystub** and watches gross shrink to net (taxes/deductions) — the teaching moment.
2. The player **allocates net pay across essentials** (housing, food, transport, utilities) *before* wants.
3. A **surprise/risk event** hits (car repair, slow week, price spike).
4. Whether they budgeted and kept a buffer decides **cover vs. shortfall** — the win condition of the round.
5. Survive → level up, earn coins, climb.

**Win / lose:**
- **Win:** reach a target (savings/net worth) within the turn limit.
- **Lose (bankruptcy):** net worth < 0 (owe more than cash + investments).
- **Lose (burnout):** happiness hits 0.

**Retention & reward systems (fold into the loop, not bolted on):** streaks, levels, coins, avatar/home **customization** (the coin sink), **leaderboards** (tap the "loud budgeting" social behavior), an in-game **economy** modeled on real price ratios, escalating **risk levels**.

**Hook:** survive enough paychecks to go from broke new hire to the Budget **GOAT** (purple goat mascot as guide).

> **⚠ SCOPE NOTE (open decision — see §12):** The four-slider model below is rich enough to become a *lifetime* wealth game (college loans → portfolios → $1M retirement), which drifts off the first-paycheck need. **Recommendation: keep the exact four-slider structure but scope the timeline to early adulthood** ("survive your first few years in the workforce; reach a stable buffer"), with investing as a *late-game unlock* rather than the main event. This keeps every mechanic, halves the balancing burden, and stays on-need.

---

## 5. The four sliders (state model)

**Cash** is the central hub; Investments, Liabilities, and Happiness are reservoirs you move cash into/out of. Jobs and markets feed the system from outside. Net worth = **cash + investments − liabilities**.

**Cash** *(never below 0)*
- **Up:** net paycheck · selling investments (then taxed) · taking a loan · windfall event
- **Down:** essentials [forced] · loan/mortgage payment [forced] · taxes due · buying investments · leisure spending
- **Key branch:** if forced outflows exceed cash → **shortfall** → auto credit-card debt or a penalty. *This is where the need statement lives in the game.*

**Investments** *(risk-free / index / growth / crypto / home equity)*
- **Up:** buying · market gains (risk-free always small +; index/growth/crypto rolled from their own probabilities) · home appreciation
- **Down:** selling · market losses
- Crypto-as-gambling must actually punish over-allocation, or it teaches "crypto = free money."

**Liabilities** *(debt principal + interest + taxes owed)*
- **Up:** new loans (student/mortgage/credit) · interest each turn · taxes assessed (income + capital gains on sales)
- **Down:** payments made · taxes paid
- Housing fork: own → mortgage liability + home asset; don't → flat rent (pure drain, no asset).

**Happiness** *(0 = lose)* — detailed in §6.

---

## 6. Happiness logic (worked example)

Happiness runs as a pipeline each turn: one guaranteed drain, conditional penalties, one player-controlled recovery, then the floor check.

**Order:** carried value → − baseline decay (always) → ± life event → − debt stress (if debt too high) → − shortfall hit (if essentials unmet) → + leisure spending (diminishing returns) → ± events/milestones → clamp 0–100 → **check ≤ 0 → burnout (lose) / else next turn**.

```python
def update_happiness(s):
    h = s.happiness
    h -= DECAY                                   # always — the pressure that forces spending
    if s.event:                      h += s.event.happiness       # ± if an event fired
    if debt_ratio(s) > STRESS_LIMIT: h -= STRESS_PENALTY          # conditional
    if s.shortfall_this_turn:        h -= SHORTFALL_PENALTY       # ties to the need
    h += leisure_gain(s.leisure_spend)           # + player's recovery lever
    for m in s.milestones_hit:       h += m.bonus
    s.happiness = clamp(h, 0, 100)
    if s.happiness <= 0:             s.game_over = "burnout"
    return s

def leisure_gain(spend):
    return GAIN_SCALE * math.sqrt(spend)         # concave: each extra $ buys less happiness
```

**Two branches that carry the design:**
- **Diminishing returns on leisure** (`sqrt`/`log`, not linear) is what makes the choice interesting: the smart play is *a little leisure often*, not one big splurge — a real, teachable habit — and it stops trivial max-ing of happiness.
- **The shortfall penalty is the bridge to the need statement:** failing to cover essentials costs *happiness*, not just cash — making "budget so you never fall short" emotionally real.

**Tuning knobs:** `DECAY` vs `GAIN_SCALE` sets how much you're *forced* to spend each turn to stay afloat — the core tension. Start decay modest, tune from playtests. Too high → money-vs-happiness is brutal; too low → happiness is ignorable.

**Design point:** happiness is the **anti-hoarding mechanic.** Without it, the winning strategy is to spend nothing and grind savings; with it, a player who never enjoys their money loses just as surely as one who goes broke.

---

## 7. Turn resolution order (8 phases)

The sliders only interact in a *sequence*; getting the order right is most of the logic. Each turn:

1. **Income** — paycheck computed gross→net; net lands in cash.
2. **Markets** — apply this turn's return to each investment class + home.
3. **Interest** — accrue on outstanding debts (liabilities up).
4. **Forced outflows** — essentials + debt minimums leave cash (run shortfall handling if short).
5. **Events** — year-end tax bill comes due; one bounded life event fires (AI narrates).
6. **Player choices** — buy/sell, extra debt payment, leisure spend, big moves (loan, house, job, school).
7. **Upkeep** — happiness decay + stress (see §6).
8. **Check** — recompute net worth; lose if < 0 or happiness = 0; win if ≥ target on the final turn.

---

## 8. Technical architecture

**Stack:** **Streamlit** (pure Python → browser, free deploy, no server/JS). The team knows Python; Streamlit is the "I know Python, I want a web app fast, ugly is fine" tool. Flask+templates or NiceGUI are fallbacks.

**The load-bearing decision — separate the engine from the UI:**
- **Engine = pure Python.** Plain functions + a state object; zero Streamlit, zero web. Paystub math, economy, allocation, events, streak/level math. **Terminal-playable before any UI exists**, and unit-testable (which also covers the "test whether concepts stuck" spec).
- **UI = a thin Streamlit skin** over the engine. Only 1–2 people touch it. The *only* Streamlit-specific concept: every button click re-runs the script top to bottom, so persistent state lives in `st.session_state`.

**The whole app is one state object passed through pure functions each turn:**
```python
state = {
  "week": 1, "cash": 0.0, "gross": 2000.0, "net": 0.0,
  "essentials": {"rent": 0, "food": 0, "transport": 0},
  "investments": {"riskfree": 0, "index": 0, "growth": 0, "crypto": 0, "home": 0},
  "liabilities": {"loans": [], "taxes_owed": 0},
  "happiness": 60, "streak": 0, "level": 1, "coins": 0,
  "event": None, "status": "ok", "history": [],
}
```
Each of the 8 phases is one `phase(state) -> state` function; `run_turn()` chains them in order. A slider is just a field; an "interaction" is which phase touches which field. **Adding a mechanic later = inserting a function at the right phase** — nothing else moves.

> **v1.1 — the state is now a class, not a dict.** The sketch above captured the idea; the built version is a `@dataclass(slots=True) GameState` (`game/state.py`) so a misspelled field raises immediately instead of silently creating junk — worth it with a team still learning Python. Access is `state.cash`, not `state["cash"]`. See the game-loop spec §3 for the full field list.

**Module layout — AS BUILT (v1.1).** The engine is implemented, terminal-playable, and covered by 18 passing tests. `app.py` (Streamlit) is **not built yet** — the engine comes first, exactly as planned. Content teammates live in `data/` + `config.py`.
```
config.py            # every tunable number (the single source of truth)
play.py              # terminal game loop (play before any UI exists)
game/                # the ENGINE (pure Python, no UI)
  formulas.py        # pure spec math (paystub, interest, gains, amortize, rounding)
  enums.py           # typo-safe GameOver / AssetClass / DebtKind / Housing
  state.py           # the GameState class + new_game()
  rng.py             # seeded randomness
  paystub.py         # Phase 1  income (gross -> net)
  economy.py         # Phases 2+3  markets + interest
  outflows.py        # Phase 4  forced bill + shortfall
  events.py          # Phase 5  year-end tax + life event
  choices.py         # Phase 6  player moves
  happiness.py       # Phase 7  the anti-hoarding meter
  engine.py          # Phase 8 checks + run_turn() (chains all 8) + milestones
data/
  events.json        # life-event wording (content, no code)
  milestones.json    # milestone bonuses (content, no code)
tests/               # worked examples, invariants, events, enums
```
*(`progression.py` from the original sketch was deferred — streak/level/coins are a retention layer for later; the engine ships the financial core only. `events.json` moved under `data/`.)*

**Deployment:** push to GitHub → Streamlit Community Cloud (free) → public URL, zero DevOps.
**Streamlit limits (all fine for a turn-based game):** awkward at shared cross-user state → **fake the leaderboard with static peer scores for the MVP**; no real-time animation (irrelevant here); limited visual polish → the "ugly is fine" tradeoff working *for* you.

---

## 9. AI integration

**Organizing principle — separate truth from voice:**
- **The engine computes truth** (all numbers, correct by construction). AI never decides these.
- **The game makes them live it** (doing the budget + hitting the consequence is the primary teacher).
- **AI is the teaching *voice*** on top — it takes numbers the engine already computed and turns them into personalized, plain-language, timely explanation. Because it only ever narrates engine-provided numbers, **it structurally cannot hallucinate a wrong tax figure or give dangerous advice.**

**Three slots where AI genuinely fits:**
1. **Consequence explainer** (highest value): one generated line in the player's own numbers after a choice.
2. **End-of-round coach:** summarizes the cycle, names the rule they followed/broke, suggests one change — this *is* the "adapts to / suggests consumer behavior" spec.
3. **Bounded ask-anything tutor** (stretch): answers budgeting questions, scoped + guardrailed.

**Steer away from:** an open-ended financial-advice chatbot (crowded, risky, off-need); AI as a forecasting oracle (thin-data problem; game money is synthetic anyway); AI generating core facts at runtime. **Reframe the "model weights / predict next week" language in the spec: zero machine learning is needed** — deterministic logic computes numbers, an LLM (one API call) explains them.

**Plugs into the architecture as another thin layer over the engine:**
```python
def coach(state, event):
    prompt = f"""You are a friendly budgeting coach inside an educational game.
Player just finished week {state['week']}. Use ONLY these numbers:
- Take-home: ${state['net']}   Rent: ${state['essentials']['rent']}
- Savings buffer: ${state['savings']}
- Surprise: {event['name']} (${event['cost']})   Result: {state['status']}
In 2-3 sentences: explain what happened in these numbers, name one budgeting
rule of thumb, suggest one concrete change. Never invent numbers.
This is educational, not financial advice."""
    return llm(prompt)   # one HTTP call (Anthropic API), returns text
```
In Streamlit: `st.write(coach(s, event))` (or `st.chat_message` for the chat look). One call per round keeps cost/latency demo-friendly; **if the API key is missing, fall back to a static recap so AI never blocks the demo.**

**Safety (bake into the wrapper):** *scope* to budgeting/game topics (refuse/redirect off-topic or harmful prompts); *ground* ("use only the numbers provided, never invent"); *disclaim* ("educational, not financial advice"). The big advantage: the game runs on **synthetic money**, so there are no real balances or account linking — the privacy/"harm the wallet" risks are largely designed out of the MVP.

**Build-time AI use:** have AI help draft the scenario bank and micro-lessons *now*, then bake them in as reviewed static content — dodging runtime risk entirely.

---

## 10. Ethical considerations (from team doc)

- **Safety:** platform (incl. AI) prioritizes safety; rebuffs/redirects harm-affiliated prompts, or ends the conversation.
- **Due diligence:** verify safety/benefit of a suggestion or lesson before serving it.
- **Integrity:** AI stays harmless and honest; never encourages harm.
- **Informed consent:** ask for consent before tracking data / sending it to an AI model.
- **Confidentiality:** user info not shared across users or externally unless the user shares it; secure from unauthorized access.
- **Transparency:** the platform/AI is clear with the user to prevent misunderstandings that could harm their plan. The **EU AI Act** framework can be used to identify high-risk AI practices.

---

## 11. Build plan (4 weeks)

**Governing principle: protect the core loop.** If a player can complete one full pay cycle (paycheck → paystub → allocate → surprise → cover-or-shortfall) by end of Week 2, the project ships. The binding constraint is **coding bandwidth, not time** — be honest about who can build; it decides whether the leaderboard is real and whether any live-AI feature is in.

**Roles (adjust to real skills):**

| Lane | Suggested owner | Owns |
|---|---|---|
| Tech lead + core loop | Dylan | game-loop state machine, paystub/economy engine, integration, final build |
| Systems + retention eng | 2nd coder | streaks/levels/coins, customization, leaderboard, math/feedback layer |
| Content + financial design | Prisha | scenarios & surprise expenses, realistic paystub numbers, prices, micro-lessons |
| Visual/UX + assets | Aicha + Shiyu | goat mascot (image asset), screen flow, copy, the >3 learning-style options |
| Testing + ethics + deliverables | Jonathan | playtest + retention/learning measurement, ethics/guardrails writeup, docs, presentation |

*Streamlit caps visual craft, so the design lane owns the mascot-as-asset, flow, and copy rather than pixel-perfect layout.*

**Timeline (map to your real deadline):**
- **Week 1 — Lock design + scaffold** *(highest-leverage week)*: finalize a one-page game-design doc (loop, paystub numbers, price list, scenario list, reward math, art direction); stand up repo + skeleton; wireframes + mascot v1; playtest/measurement plan. **Gate:** design locked, repo runs, one paystub calculation works.
- **Week 2 — Vertical slice** *(make-or-break)*: one complete pay cycle playable end-to-end, rough UI; content handed off; core screens + final mascot; first internal playtest. **Gate:** a teammate can play one cycle and it teaches gross→net + essentials budgeting. If not, cut scope now.
- **Week 3 — Layer systems + content + polish**: multi-cycle progression, retention systems, customization, math feedback, leaderboard (real or static); full scenario set; UI polish + learning-style options; recruit ~5–10 outside playtesters + collect data. **Gate:** feature-complete beta.
- **Week 4 — Integrate, test, ship**: bug-fix + balance, then **freeze features**; turn playtest data into results; finalize ethics; write docs; build + rehearse the presentation; keep a slippage buffer.

**Scope traps to watch:** "intricate economy" and AI ambitions balloon fast — a *believable* economy (real ratios, a few choices) teaches as well as an intricate one and ships. Leaderboards are secretly expensive (accounts + backend) — fake for MVP. Guard the Week-4 buffer.

---

## 12. Open decisions (resolve as a team)

*Status as of v1.1 (engine built). See `docs/implementation-status.md` for details.*

1. **Timeline scope — early-career vs full lifetime.** ✅ **DECIDED: early-career.** 60 in-game months; investing kept small. Matches the need statement and the differentiation guide.
2. **Tax timing.** ✅ **DECIDED & BUILT: withholding on the paystub.** Net lands in cash; a small year-end reconciliation + capital-gains on sales. The gross→net moment is preserved.
3. **Leaderboard for MVP.** ⏳ **Unbuilt (plan stands):** fake with static peer scores; build real only if a coder has spare time. No leaderboard code yet.
4. **AI scope.** ⏳ **Unbuilt (plan stands):** deterministic teaching is done and fully reliable; the AI coach is the next differentiator to add.
5. **(New, v1.1) Bankruptcy rule.** ✅ **DECIDED & BUILT:** you lose by failing to cover essentials 3 months running (a cash-flow failure), not by negative net worth. Net worth is the *win* metric.
6. **(New, v1.1) Difficulty & equal paths.** ✅ **DECIDED & BUILT:** rebalanced from ~90% bankruptcy to ~50% win under skilled play; the two paths are equalised via per-path win targets ($23k A / $68k B).
7. **(New, v1.1) Layoffs.** ✅ **DECIDED:** rare, and you recover by taking a new job (manual). A UI/coach must prompt this.
8. **(New, v1.1) Graduation effect of GoToSchool.** ⏳ **Still open** — finishing school doesn't yet raise gross.

---

## 13. Key references

**Read-first (the design-defining debate + what works):**
- Fernandes, Lynch & Netemeyer (2014). *Financial Literacy, Financial Education, and Downstream Financial Behaviors.* Management Science, 60(8), 1861–1883.
- Kaiser, Lusardi, Menkhoff & Urban (2022). *Financial education affects financial knowledge and downstream behaviors.* Journal of Financial Economics, 145(2), 255–272.
- Bertrand & Morse (2011). *Information Disclosure, Cognitive Biases, and Payday Borrowing.* The Journal of Finance, 66(6), 1865–1893.
- Drexler, Fischer & Schoar (2014). *Keeping It Simple: Financial Literacy and Rules of Thumb.* American Economic Journal: Applied Economics, 6(2), 1–31.

**Foundation & landscape:**
- Lusardi & Mitchell (2014). *The Economic Importance of Financial Literacy: Theory and Evidence.* Journal of Economic Literature, 52(1), 5–44.
- *Financial literacy among young college students: Advancements and future directions.* F1000Research (2025), 14:113. (Systematic review; flags budgeting & digital tools as an under-explored gap.)

**Solution landscape / current context:**
- CFPB report on Earned Wage Access (2024–25).
- Plotline, *Retention rates for mobile apps by industry* (fintech) — the ~77%-in-3-days / ~90%-in-30-days abandonment reality.
- Bank of America (2026). *2026 Better Money Habits Study — Gen Z & The Cost of Adulting* (Ipsos; n≈1,133 Gen Z; ±3.0 pp). Source of the 42% paycheck-to-paycheck and family-support figures. Treat as industry survey, not peer-reviewed.
- Federal Reserve Bank of New York (2026). *Quarterly Report on Household Debt and Credit: 2026 Q1* ($1.25T credit card debt).

*Source-quality note: keep the peer-reviewed papers as load-bearing evidence; use BofA/Ramsey/industry pieces for current texture only. The IJFMR paper and the unverifiable `cfdm.jcx.au` link should not carry any load-bearing claim.*

---

*End of handoff. **v1.1 update:** the `/game` engine is built and terminal-playable (`python play.py`), covered by 18 passing tests, with the starting numbers locked and balanced. The next steps are now the **Streamlit UI** over the engine and the **`coach()` AI layer** — see `docs/implementation-status.md` for the current state and what's next.*
