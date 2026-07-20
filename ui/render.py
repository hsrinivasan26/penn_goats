"""HTML render helpers -- turn game state into markup for st.markdown(unsafe_allow_html=True)."""

import config


# --- formatting ---

def money(n) -> str:
    n = int(round(n))
    return f"-${abs(n):,}" if n < 0 else f"${n:,}"


def kmoney(n) -> str:
    """Abbreviated for ring labels: $3.7k, $24k, $500."""
    n = int(round(n))
    a = abs(n)
    if a >= 1000:
        s = f"${a/1000:.1f}k" if a < 100000 else f"${a//1000}k"
    else:
        s = f"${a}"
    return "-" + s if n < 0 else s


def happiness_color(h: int) -> str:
    """Sky-blue when high, darkening toward near-black as it drops."""
    t = max(0.0, min(1.0, h / 100))
    lo = (18, 34, 46)      # near-black blue at 0
    hi = (56, 189, 248)    # sky-blue at 100
    r, g, b = (int(lo[i] + (hi[i] - lo[i]) * t) for i in range(3))
    return f"rgb({r},{g},{b})"


# --- the four rings (vertical rail) ---

_CIRC = 175.9  # 2 * pi * 28


def _ring(value_label, pct, color, name, tooltip_html) -> str:
    pct = max(0.0, min(1.0, pct))
    off = _CIRC * (1 - pct)
    return f'''<div class="ringitem">
      <div class="ring"><svg width="70" height="70">
        <circle cx="35" cy="35" r="28" stroke="#12151c" stroke-width="7" fill="none"/>
        <circle cx="35" cy="35" r="28" stroke="{color}" stroke-width="7" fill="none" stroke-linecap="round"
          stroke-dasharray="{_CIRC}" stroke-dashoffset="{off:.1f}"/></svg>
        <div class="rc"><span class="rv" style="color:{color}">{value_label}</span></div></div>
      <div class="rmeta"><div class="rn">{name}</div></div>
      <div class="tip">{tooltip_html}</div>
    </div>'''


def _cash_tip(state) -> str:
    nw = state.net_worth()
    goal = state.target
    streak = state.consecutive_shortfalls
    if streak >= max(1, config.BANKRUPTCY_SHORTFALL_STREAK - 1):
        return (f"<div class='tt' style='color:#ef4444'>&#9888; About to lose</div>"
                f"<p>Missed essentials {streak} months running — cover essentials or it's game over.</p>")
    if nw < 0:
        return f"<div class='tt'>Net worth {money(nw)}</div><p>Below zero from debt — not a loss. Goal: {money(goal)}.</p>"
    return f"<div class='tt'>Net worth {money(nw)}</div><p>{money(max(0, goal - nw))} to your {money(goal)} goal.</p>"


def rings_html(state) -> str:
    inv = state.investments_total()
    liab = state.liabilities_total()
    nw = state.net_worth()
    ess = (state.mortgage_payment if state.housing == "own" else state.rent) \
        + state.food + state.transport + state.utilities
    annual = max(1, state.gross_month * 12)

    rings = "".join([
        _ring(kmoney(state.cash), state.cash / (3 * max(1, ess)), "#34d399", "Cash", _cash_tip(state)),
        _ring(kmoney(inv), inv / max(1, state.target), "#f5b642", "Investments",
              "<div class='tt'>Investments</div><p>Value rises and falls with the market.</p>"),
        _ring(kmoney(liab), liab / annual, "#ef4444", "Debt",
              f"<div class='tt'>Debt · {money(liab)}</div><p>What you owe. Interest is added each month.</p>"),
        _ring(str(state.happiness), state.happiness / 100, happiness_color(state.happiness), "Happiness",
              "<div class='tt'>Happiness</div><p>Falls a little each month. At 0 you burn out (a loss).</p>"),
    ])
    nwc = "#34d399" if nw >= 0 else "#ef4444"
    return (f'<div class="rail"><div class="railcap">Your standing</div>{rings}'
            f'<div class="nwrail"><div class="k">Net worth</div>'
            f'<div class="v" style="color:{nwc}">{money(nw)}</div></div></div>')


# --- paycheck reveal ---

def paystub_html(stub) -> str:
    if not stub or stub["gross"] == 0:
        return ('<div class="pay"><div class="cap">Payday</div>'
                '<p style="color:#9aa0ac;margin:8px 0 0">No paycheck this month — you\'re between jobs.</p></div>')
    return f'''<div class="pay"><div class="cap">Payday</div>
      <div class="flow">
        <div class="blk"><div class="k">Offer</div><div class="g">{money(stub['gross'])}</div></div>
        <div class="arrow">&#8594;</div>
        <div class="blk"><div class="k">Take-home</div><div class="n">{money(stub['net'])}</div></div>
        <div class="cuts">
          <div class="r"><span>Federal</span><span class="vd">{money(-stub['federal'])}</span></div>
          <div class="r"><span>State</span><span class="vd">{money(-stub['state'])}</span></div>
          <div class="r"><span>FICA</span><span class="vd">{money(-stub['fica'])}</span></div>
        </div>
      </div></div>'''


# --- this month's bill (make "cash to work with" transparent) ---

def bill_html(state, month) -> str:
    """A plain statement showing exactly how this month's cash was reached:
    carry-over + take-home + cash events, minus the essentials, debt minimums, and taxes."""
    if not month:
        return ""
    stub = month.get("stub") or {}
    bill = month.get("bill") or {}
    event = month.get("event")
    tax = month.get("tax")
    net = int(stub.get("net", 0))
    ev_cash = int(event["cash_delta"]) if event else 0

    money_in = [("Cash carried over", int(month.get("start_cash", 0)))]
    if net:
        money_in.append(("Take-home pay", net))
    if ev_cash > 0:
        money_in.append((event["label"], ev_cash))

    housing_label = "Mortgage" if state.housing == "own" else "Rent"
    money_out = [(housing_label, int(bill.get("housing", 0))),
                 ("Food", int(state.food)),
                 ("Transport", int(state.transport)),
                 ("Utilities", int(state.utilities))]
    for slot, amt in (bill.get("debt_minimums") or {}).items():
        name = str(getattr(slot, "value", slot)).replace("_", " ").title()
        money_out.append((f"{name} (min. payment)", int(amt)))
    if tax and tax.get("paid"):
        money_out.append(("Year-end taxes", int(tax["paid"])))
    if ev_cash < 0:
        money_out.append((event["label"], -ev_cash))

    def rows(items, cls, sign):
        out = []
        for label, amt in items:
            if not amt:
                continue
            v = ("+" if sign > 0 else "−") + money(amt)
            out.append(f"<div class='billrow'><span>{label}</span><span class='{cls}'>{v}</span></div>")
        return "".join(out)

    short = ""
    if bill.get("shortfall"):
        short = (f"<div class='billshort'>&#9888; You were short by {money(int(bill.get('gap', 0)))} — "
                 f"the gap was borrowed onto a credit card at {int(config.APR['credit_card'] * 100)}% APR.</div>")

    return (f"<details class='bill' open><summary class='billcap'>This month's money "
            f"<span class='billtot'>{money(int(state.cash))} to work with</span></summary>"
            f"{rows(money_in, 'bin', +1)}<div class='billsep'></div>"
            f"{rows(money_out, 'bout', -1)}{short}</details>")


# --- milestone banner ---

def milestone_html(m) -> str:
    if not m:
        return ""
    return (f'<div class="milestone"><div><span class="mlab">★ Milestone reached</span>'
            f'<div class="mtitle">{m["label"]}</div></div>'
            f'<div class="mbonus">+{m["bonus"]} happiness</div></div>')


# --- this-month events ---

def event_html(payload) -> str:
    if not payload:
        return ""
    bill, event, tax = payload["bill"], payload["event"], payload["tax"]
    if event and event.get("key") == "quiet":
        event = None                      # a calm month needs no banner
    parts = []
    if bill and bill.get("shortfall"):
        parts.append(f'<div class="shortfall">&#9888; Short by {money(bill["gap"])} on essentials '
                     f'— the gap was borrowed onto a credit card (24% APR).</div>')
    if tax:
        parts.append(f'<div class="taxline">Year-end taxes: paid {money(tax["paid"])}'
                     + (f', still owed {money(tax["still_owed"])}' if tax["still_owed"] else '') + '.</div>')
    if event:
        if event["cash_delta"]:
            detail = money(event["cash_delta"])
        elif event["happiness_delta"]:
            detail = f"{event['happiness_delta']:+d} mood"
        else:
            detail = ""
        neg = event["cash_delta"] < 0 or event["happiness_delta"] < 0 or event["layoff"]
        cls = "ev-neg" if neg else "ev-pos"
        extra = " · you're laid off — find a new job" if event["layoff"] else ""
        parts.append(f'<div class="event {cls}"><span class="lab">Life happens</span>'
                     f'<div class="etitle">{event["label"]}{(" · " + detail) if detail else ""}{extra}</div></div>')
    return "".join(parts)


# --- results: net-worth-over-time chart ---

def results_chart_html(state) -> str:
    """Net worth over every month played, as a hand-drawn SVG. All geometry is derived from
    the data, so the same code renders a win or a loss."""
    hist = state.history or []
    vals = [int(h["net_worth"]) for h in hist]
    turns = [int(h["turn"]) for h in hist]
    if len(vals) < 2:
        return ("<div class='chartwrap' style='text-align:center;color:#6b7280;font-size:13px;"
                "padding:26px'>Not enough history to chart yet.</div>")

    target = int(state.target)
    lo, hi = min(min(vals), 0), max(max(vals), target)
    pad = (hi - lo or 1) * 0.08
    lo, hi = lo - pad, hi + pad
    span = hi - lo or 1

    X0, X1, YT, YB = 40, 500, 24, 170
    n = len(vals)
    xs = [X0 + (X1 - X0) * i / (n - 1) for i in range(n)]
    ys = [YB - (YB - YT) * (v - lo) / span for v in vals]

    line_pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in zip(xs, ys))
    area_d = ("M" + f"{xs[0]:.1f},{ys[0]:.1f}"
              + "".join(f" L{x:.1f},{y:.1f}" for x, y in zip(xs[1:], ys[1:]))
              + f" L{xs[-1]:.1f},{YB} L{xs[0]:.1f},{YB} Z")

    gy = YB - (YB - YT) * (target - lo) / span      # goal line y
    zy = YB - (YB - YT) * (0 - lo) / span           # zero line y
    end_color = "#34d399" if state.net_worth() >= target else "#ef4444"

    return f'''<div class="chartwrap"><svg viewBox="0 0 520 190" role="img" aria-label="Net worth over time">
      <defs>
        <linearGradient id="pgln" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0" stop-color="#ef4444"/><stop offset="0.35" stop-color="#f5b642"/>
          <stop offset="0.7" stop-color="#34d399"/><stop offset="1" stop-color="#8b6dff"/>
        </linearGradient>
        <linearGradient id="pgar" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stop-color="#34d399" stop-opacity="0.22"/><stop offset="1" stop-color="#34d399" stop-opacity="0"/>
        </linearGradient>
      </defs>
      <line x1="40" y1="{gy:.1f}" x2="500" y2="{gy:.1f}" stroke="#5a4a1a" stroke-dasharray="4 4"/>
      <text x="498" y="{gy - 6:.1f}" text-anchor="end" fill="#c99b3a" font-size="10" font-family="Inter">{kmoney(target)} goal</text>
      <line x1="40" y1="{zy:.1f}" x2="500" y2="{zy:.1f}" stroke="#242a35"/>
      <text x="36" y="{zy + 4:.1f}" text-anchor="end" fill="#6b7280" font-size="10" font-family="Inter">$0</text>
      <path d="{area_d}" fill="url(#pgar)"/>
      <polyline points="{line_pts}" fill="none" stroke="url(#pgln)" stroke-width="3" stroke-linejoin="round" stroke-linecap="round"/>
      <circle cx="{xs[0]:.1f}" cy="{ys[0]:.1f}" r="4" fill="#ef4444"/>
      <circle cx="{xs[-1]:.1f}" cy="{ys[-1]:.1f}" r="5" fill="{end_color}" stroke="#0e1117" stroke-width="2"/>
      <text x="40" y="185" fill="#6b7280" font-size="10" font-family="Inter">Month {turns[0]}</text>
      <text x="500" y="185" text-anchor="end" fill="#6b7280" font-size="10" font-family="Inter">Month {turns[-1]}</text>
    </svg></div>'''
