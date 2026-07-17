"""Chryseos -- Streamlit UI over the pure-Python engine.

Screen routing lives in st.session_state; ALL game logic lives in game/ -- this file only
renders state and collects the player's moves.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import random
import streamlit as st

try:                                   # load .env so GEMINI_API_KEY reaches the AI features
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

import config
from game.state import new_game
from game.rng import SeededRNG
from game.formulas import leisure_happiness, amortize
from game import choices
from game import mcq

import style
import render
import turn
import titles
import coach
import quiz

st.set_page_config(page_title="Chryseos", layout="wide")
style.inject_css()

ss = st.session_state
if "screen" not in ss:
    ss.screen = "title"
if "earned_titles" not in ss:
    ss.earned_titles = set()

PATH_META = {
    "A": {"name": "Starting from scratch", "desc": "No degree, no debt. Lower pay, but a clean slate."},
    "B": {"name": "Fresh graduate", "desc": "A degree and a bigger paycheck — and a $30k loan to dig out of."},
}


def go(screen):
    ss.screen = screen


def start_game(path):
    seed = random.randint(0, 10**9)
    ss.state = new_game(path, seed=seed)
    ss.rng = SeededRNG(seed)
    ss.month = turn.begin_month(ss.state, ss.rng)
    ss.last_milestone = None
    go("play")


# --------------------------------------------------------------------------
# Screens
# --------------------------------------------------------------------------

def screen_title():
    st.markdown(
        "<div class='title-wrap'>"
        "<img class='title-logo' src='app/static/logo.svg' alt='Chryseos'/>"
        "<div class='title-brand'>Chryseos</div>"
        "<div class='title-hook'>From broke new hire to Budget GOAT.</div>"
        "<div class='title-tag'>A money game about your first real paychecks.</div>"
        "</div>", unsafe_allow_html=True)
    c = st.columns([3, 2, 3])
    with c[1]:
        if st.button("Start", type="primary", use_container_width=True):
            go("choose"); st.rerun()
        if st.button("How to play", use_container_width=True):
            go("howto"); st.rerun()
        if st.button("Money quiz", use_container_width=True):
            go("quiz"); st.rerun()
        if st.button("Titles", use_container_width=True):
            go("titles"); st.rerun()


def screen_choose():
    st.markdown(
        "<h2 style='text-align:center'>Choose your start</h2>"
        "<p style='text-align:center;color:#9aa0ac'>Two different lives — both winnable, about equally tough.</p>",
        unsafe_allow_html=True)
    cols = st.columns(2, gap="large")
    for col, key in zip(cols, ["A", "B"]):
        cfg = config.PATHS[key]
        meta = PATH_META[key]
        debt = cfg["student_loan"]["principal"] if cfg["student_loan"] else 0
        with col:
            st.markdown(f"""<div class='pcard'>
              <div class='pn'>{meta['name']}</div>
              <div class='pd'>{meta['desc']}</div>
              <div class='pstats'>
                <div class='pstat'><div class='sl'>Pay / mo</div><div class='sv'>{render.money(cfg['gross_month'])}</div></div>
                <div class='pstat'><div class='sl'>Debt</div><div class='sv'>{render.money(debt)}</div></div>
                <div class='pstat'><div class='sl'>Cash</div><div class='sv'>{render.money(cfg['cash'])}</div></div>
                <div class='pstat'><div class='sl'>Goal</div><div class='sv'>{render.money(cfg.get('target', config.TARGET))}</div></div>
              </div></div>""", unsafe_allow_html=True)
            if st.button("Start this life", key=f"start_{key}", type="primary", use_container_width=True):
                start_game(key); st.rerun()
    st.write("")
    if st.button("← Back"):
        go("title"); st.rerun()


# --------------------------------------------------------------------------
# Action dialogs -- each opens as a modal (st.dialog), calls one engine choice,
# then reruns to close.
# --------------------------------------------------------------------------

ASSET_DESC = {
    "index":    "≈ 0.7%/mo · steady",
    "growth":   "≈ 1.2%/mo · bigger swings",
    "crypto":   "≈ 2%/mo · very high risk",
    "riskfree": "≈ 0.3%/mo · never loses",
}


def _cash_line(s):
    st.markdown(f"<div class='dlgcash'>Available cash: <b>{render.money(int(s.cash))}</b></div>",
                unsafe_allow_html=True)


def _amount_slider(label, cap, default, key):
    cap = int(cap)
    step = 50 if cap >= 500 else 10 if cap >= 100 else 1
    return st.slider(label, 0, cap, min(int(default), cap), step, key=key)


@st.dialog("Invest")
def dlg_invest():
    s = ss.state
    _cash_line(s)
    if int(s.cash) <= 0:
        st.caption("No cash to invest right now."); return
    cls = st.selectbox("Asset", list(ASSET_DESC), format_func=str.capitalize, key="di_cls")
    st.caption(ASSET_DESC[cls])
    amt = _amount_slider("Amount ($)", s.cash, min(200, int(s.cash)), "di_amt")
    st.caption("Gains are taxed only when you sell.")
    if st.button(f"Invest {render.money(amt)}", type="primary", disabled=amt <= 0, use_container_width=True):
        choices.invest(s, int(amt), cls); st.rerun()


@st.dialog("Sell")
def dlg_sell():
    s = ss.state
    _cash_line(s)
    held = {c: v for c, v in s.investments.items() if v > 0}
    if not held:
        st.caption("Nothing to sell yet."); return
    cls = st.selectbox("Asset", list(held), format_func=lambda k: k.capitalize(), key="ds_cls")
    bal = int(held[cls])
    amt = _amount_slider("Amount ($)", bal, bal, "ds_amt")
    if st.button(f"Sell {render.money(amt)}", type="primary", disabled=amt <= 0, use_container_width=True):
        choices.sell(s, int(amt), cls); st.rerun()


@st.dialog("Treat yourself")
def dlg_leisure():
    s = ss.state
    _cash_line(s)
    if int(s.cash) <= 0:
        st.caption("No cash for fun right now."); return
    amt = _amount_slider("Spend on fun ($)", s.cash, min(40, int(s.cash)), "dl_amt")
    st.markdown(f"<div class='hpreview'>Happiness this month <b>+{leisure_happiness(int(amt))}</b></div>",
                unsafe_allow_html=True)
    if st.button(f"Spend {render.money(amt)}", type="primary", disabled=amt <= 0, use_container_width=True):
        choices.leisure(s, int(amt)); st.rerun()


@st.dialog("Pay down a debt")
def dlg_paydebt():
    s = ss.state
    _cash_line(s)
    debts = {k: v for k, v in s.liabilities.items() if v and v["principal"] > 0}
    if not debts:
        st.caption("No debts right now — nothing to pay down."); return
    if int(s.cash) <= 0:
        st.caption("No cash to pay debt right now."); return
    labels = {f"{k.replace('_', ' ').title()} · {render.money(v['principal'])} @ {int(v['apr']*100)}%": k
              for k, v in debts.items()}
    pick = st.selectbox("Debt", list(labels), key="dd_sel")
    slot = labels[pick]
    cap = min(int(s.cash), int(debts[slot]["principal"]))
    amt = _amount_slider("Extra payment ($)", cap, min(200, cap), "dd_amt")
    st.caption("Extra payments come straight off the principal.")
    if st.button(f"Pay {render.money(amt)}", type="primary", disabled=amt <= 0, use_container_width=True):
        choices.pay_debt(s, int(amt), slot); st.rerun()


@st.dialog("Job & moves")
def dlg_jobmoves():
    s = ss.state
    _cash_line(s)
    st.markdown("**Change jobs** — swap to a new salary, or recover from a layoff.")
    g = st.number_input("New monthly gross ($)", 0, 20000, int(s.gross_month) or 3000, 100, key="dj_g")
    if st.button("Take this job", key="dj_btn", use_container_width=True):
        choices.change_job(s, int(g)); st.rerun()
    st.divider()
    st.markdown("**Buy a house** — trade rent for a mortgage and start building equity.")
    cash = int(s.cash)
    if s.housing == "own":
        st.caption("You already own your home.")
    else:
        price = st.number_input("Home price ($)", 80_000, 400_000, 200_000, 10_000, key="dj_price")
        down = st.number_input("Down payment ($)", 0, cash, min(cash, 20_000), 1_000, key="dj_down")
        loan = max(0, int(price) - int(down))
        pay = amortize(loan, config.APR["mortgage"] / 12, config.MORTGAGE_TERM_MONTHS)
        st.caption(f"Loan {render.money(loan)} at {config.APR['mortgage'] * 100:.1f}% → about "
                   f"{render.money(pay)}/mo (you pay {render.money(s.rent)} rent now).")
        ok = 0 <= int(down) <= cash and int(price) >= int(down)
        if st.button("Buy this house", key="dj_house_btn", disabled=not ok, use_container_width=True):
            choices.buy_house(s, int(price), int(down)); st.rerun()

    st.divider()
    st.markdown("**Buy a car** — cash for now (financing comes later).")
    if cash <= 0:
        st.caption("No cash for a car right now.")
    else:
        car = _amount_slider("Spend on a car ($)", s.cash, min(cash, 2000), "dj_car")
        if st.button("Buy car", key="dj_car_btn", disabled=car <= 0, use_container_width=True):
            choices.buy_car(s, int(car)); st.rerun()


_ACTIONS = [
    ("Invest", dlg_invest),
    ("Sell", dlg_sell),
    ("Treat yourself", dlg_leisure),
    ("Pay debt", dlg_paydebt),
    ("Job & moves", dlg_jobmoves),
]


def _actions(s):
    if not s.employed:
        st.warning("You're between jobs — no paycheck until you find work (open **Job & moves**).")
    st.markdown(f"<div class='amsg'>Your move — cash to work with: <b>{render.money(int(s.cash))}</b></div>",
                unsafe_allow_html=True)
    cols = st.columns(len(_ACTIONS))
    for col, (label, dlg) in zip(cols, _ACTIONS):
        if col.button(label, use_container_width=True, key=f"open_{label}"):
            dlg()


def screen_play():
    s = ss.state
    quiz.prefetch(s.turn)          # warm this day's quiz bank in the background (no stall)
    st.markdown(f"<div class='apphead'><b>Chryseos</b> &nbsp;·&nbsp; Month {s.turn} of {config.TURN_LIMIT} "
                f"&nbsp;·&nbsp; goal {render.money(s.target)}</div>", unsafe_allow_html=True)
    left, right = st.columns([3, 1], gap="large")
    with right:
        st.markdown(render.rings_html(s), unsafe_allow_html=True)
    with left:
        st.markdown(render.paystub_html(ss.month["stub"] if ss.month else None), unsafe_allow_html=True)
        events = render.event_html(ss.month)
        if events:
            st.markdown(events, unsafe_allow_html=True)
        milestone = render.milestone_html(ss.get("last_milestone"))
        if milestone:
            st.markdown(milestone, unsafe_allow_html=True)
        _actions(s)
        st.write("")
        if st.button("End the month ▶", type="primary"):
            turn.end_month(s)
            ss.last_milestone = s._milestone      # capture before begin_month clears it
            if s.game_over is not None:
                go("results")
            else:
                ss.month = turn.begin_month(s, ss.rng)
            st.rerun()


def screen_howto():
    st.markdown("<h2 style='margin-bottom:2px'>How it works</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color:#9aa0ac;font-size:13.5px;margin:2px 0 14px'>"
                "Five years, one month at a time. Each month:</p>", unsafe_allow_html=True)
    steps = [
        ("1", "A paycheck arrives", "See what's really left after taxes — take-home, not the offer."),
        ("2", "Essentials come out", "Rent, food, transport, and utilities are paid automatically."),
        ("3", "Life happens", "A surprise hits — a repair, a bonus, sometimes a layoff."),
        ("4", "You choose", "Invest, pay down debt, treat yourself, or make a big move."),
    ]
    cells = "".join(f"<div class='step'><div class='no'>{n}</div><div><div class='st'>{t}</div>"
                    f"<div class='sd'>{d}</div></div></div>" for n, t, d in steps)
    st.markdown(f"<div class='steps'>{cells}</div>", unsafe_allow_html=True)
    st.markdown(f"<p style='color:#9aa0ac;font-size:13.5px;margin:18px 0 0'>Reach your net-worth goal by month "
                f"{config.TURN_LIMIT} to win. Run out of cash for too long, or let happiness hit zero, and it's "
                "over. Watch your four rings:</p>", unsafe_allow_html=True)
    st.markdown(
        "<div class='legend'>"
        "<span><i style='background:#34d399'></i>Cash — money on hand</span>"
        "<span><i style='background:#f5b642'></i>Investments — grows or shrinks</span>"
        "<span><i style='background:#ef4444'></i>Debt — what you owe</span>"
        "<span><i style='background:#38bdf8'></i>Happiness — 0 = burnout</span>"
        "</div>", unsafe_allow_html=True)
    st.write("")
    if st.button("← Back to menu"):
        go("title"); st.rerun()


def screen_titles():
    earned = ss.earned_titles
    total = len(titles.TITLES)
    got = len(earned & {t["id"] for t in titles.TITLES})
    pct = int(round(100 * got / total)) if total else 0

    st.markdown("<h2 style='margin-bottom:2px'>Your titles</h2>", unsafe_allow_html=True)
    st.markdown(
        "<div class='tprog'><span style='color:#9aa0ac;font-size:13px'>Earn them by how you play — "
        f"collected across every run this session.</span><span class='pv'>{got} / {total} earned</span></div>",
        unsafe_allow_html=True)
    st.markdown(f"<div class='tbarwrap'><i style='width:{pct}%'></i></div>", unsafe_allow_html=True)

    tiles = []
    for t in titles.TITLES:
        is_earned = t["id"] in earned
        cls = "win" if (is_earned and t["kind"] == "win") else "earned" if is_earned else "locked"
        badge = "WIN" if t["kind"] == "win" else "LOSS" if t["kind"] == "loss" else ""
        bdg = f"<span class='bdg'>{badge}</span>" if badge else ""
        tiles.append(f"<div class='ttile {cls}'>{bdg}<div class='ic'>{t['icon']}</div>"
                     f"<div class='tn'>{t['name']}</div><div class='tc'>{t['blurb']}</div></div>")
    st.markdown(f"<div class='tgrid'>{''.join(tiles)}</div>", unsafe_allow_html=True)
    st.write("")
    if st.button("← Back to menu"):
        go("title"); st.rerun()


def screen_results():
    s = ss.state
    outcome = s.game_over.value
    earned_now = titles.earned_ids(s)
    ss.earned_titles |= earned_now
    look = {
        "win":        ("#34d399", "You did it", "Budget <span class='p'>GOAT</span>"),
        "bankruptcy": ("#ef4444", "Bankrupt", "In Over Your Head"),
        "burnout":    ("#fb7185", "Burned out", "Ran on Empty"),
        "timeout":    ("#f5b642", "Time's up", "Treading Water"),
    }[outcome]
    st.markdown(
        f"<div class='rbanner'><span class='rbadge' style='color:{look[0]};"
        f"background:{look[0]}1a;border:1px solid {look[0]}55'>{look[1]}</span>"
        f"<h2>{look[2]}</h2><div class='rs'>{render.money(s.net_worth())} net worth after "
        f"{s.turn} months · goal {render.money(s.target)}</div></div>", unsafe_allow_html=True)

    st.markdown(render.results_chart_html(s), unsafe_allow_html=True)

    won = s.net_worth() >= s.target
    nwc = "#34d399" if s.net_worth() >= 0 else "#ef4444"
    st.markdown(
        "<div class='rstats'>"
        f"<div class='rstat'><div class='rl'>Final net worth</div>"
        f"<div class='rv' style='color:{nwc}'>{render.money(s.net_worth())}</div></div>"
        f"<div class='rstat'><div class='rl'>Goal</div>"
        f"<div class='rv'>{render.money(s.target)}{' ✓' if won else ''}</div></div>"
        f"<div class='rstat'><div class='rl'>Months</div><div class='rv'>{s.turn}</div></div>"
        f"<div class='rstat'><div class='rl'>Happiness</div>"
        f"<div class='rv' style='color:#38bdf8'>{s.happiness}</div></div>"
        "</div>", unsafe_allow_html=True)

    # cached so reruns don't re-hit the model
    if ss.get("coach_for") != id(s):
        with st.spinner("Your coach is reviewing your run…"):
            ss.coach_text, ss.coach_is_ai = coach.overview(s, outcome)
        ss.coach_for = id(s)
    ct = "Your coach · AI" if ss.coach_is_ai else "Your coach"
    st.markdown(f"<div class='coach'><div><div class='ct'>{ct}</div>"
                f"<p>{ss.coach_text}</p></div></div>", unsafe_allow_html=True)

    if earned_now:
        chips = "".join(f"<span class='tchip'>{t['icon']} {t['name']}</span>"
                        for t in titles.TITLES if t["id"] in earned_now)
        st.markdown(f"<div class='tchips'>Titles earned{chips}</div>", unsafe_allow_html=True)

    st.write("")
    cc = st.columns([1, 1, 1, 2])
    if cc[0].button("Play again", type="primary"):
        go("choose"); st.rerun()
    if cc[1].button("Titles"):
        go("titles"); st.rerun()
    if cc[2].button("Main menu"):
        go("title"); st.rerun()


def _start_quiz():
    day = ss.get("quiz_day", 0)
    with st.spinner("Putting together today's questions…"):
        topic, bank, used_ai = quiz.build_daily_quiz(day, seed=random.randint(0, 10**6))
    ss.quiz = mcq.Quiz(bank)
    ss.quiz_topic, ss.quiz_ai = topic, used_ai
    ss.quiz_phase, ss.quiz_feedback = "answer", None


def screen_quiz():
    q = ss.get("quiz")

    # start view
    if q is None:
        day = ss.get("quiz_day", 0)
        topic = quiz.prefetch(day)      # warm the bank while the player reads
        st.markdown("<h2 style='margin-bottom:2px'>Money quiz</h2>"
                    f"<p style='color:#9aa0ac;font-size:13.5px'>Today's topic: "
                    f"<b style='color:#e8e8ea'>{topic.title()}</b> — 8–10 questions, easy to hard. "
                    "Pass mark is 65%.</p>", unsafe_allow_html=True)
        c = st.columns([1, 1, 3])
        if c[0].button("Start quiz", type="primary"):
            _start_quiz(); st.rerun()
        if c[1].button("← Menu"):
            go("title"); st.rerun()
        return

    # results view
    if q.finished and ss.get("quiz_phase") != "review":
        res = q.results()
        passed = res["passed_gate"]
        col = "#34d399" if passed else "#ef4444"
        st.markdown(
            f"<div class='rbanner'><span class='rbadge' style='color:{col};background:{col}1a;"
            f"border:1px solid {col}55'>{'PASSED' if passed else 'NOT YET'}</span>"
            f"<h2>{res['score']} / {res['total']} · {res['percent']}%</h2>"
            f"<div class='rs'>{mcq.verdict_message(res['percent'])}</div></div>", unsafe_allow_html=True)
        c = st.columns([1, 1, 3])
        if c[0].button("New quiz", type="primary"):
            ss.quiz_day = ss.get("quiz_day", 0) + 1
            ss.quiz = None; st.rerun()
        if c[1].button("← Menu"):
            ss.quiz = None; go("title"); st.rerun()
        return

    # review view
    if ss.get("quiz_phase") == "review":
        fb = ss.quiz_feedback
        p = fb["prompt"]
        st.markdown(f"<div class='amsg'>Question {p['number']} of {p['total']}</div>", unsafe_allow_html=True)
        st.markdown(f"**{p['stem']}**")
        for opt in p["options"]:
            oid = opt["id"]
            if oid == fb["correct_option_id"]:
                st.markdown(f"<div class='qopt qgood'>✓ {oid}. {opt['text']}</div>", unsafe_allow_html=True)
            elif oid == fb["chosen"] and not fb["correct"]:
                st.markdown(f"<div class='qopt qbad'>✗ {oid}. {opt['text']}</div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div class='qopt'>{oid}. {opt['text']}</div>", unsafe_allow_html=True)
        verdict = "Correct!" if fb["correct"] else f"Not quite — the answer was {fb['correct_option_id']}."
        st.markdown(f"<div class='qexpl'><b>{verdict}</b> {fb['explanation']}</div>", unsafe_allow_html=True)
        if st.button("See results" if q.finished else "Next question ▶", type="primary"):
            ss.quiz_phase, ss.quiz_feedback = "answer", None
            st.rerun()
        return

    # answer view
    p = q.current_prompt()
    item = q.current()
    diff = mcq.DIFFICULTY_LABELS.get(item.difficulty.lower(), item.difficulty.title())
    src = "AI" if ss.get("quiz_ai") else "practice set"
    st.markdown(f"<div class='amsg'>Question {p['number']} of {p['total']} · "
                f"{ss.quiz_topic.title()} · {diff} · {src}</div>", unsafe_allow_html=True)
    st.markdown(f"**{p['stem']}**")
    labels = {opt["id"]: f"{opt['id']}.  {opt['text']}" for opt in p["options"]}
    choice = st.radio("Choose one:", [opt["id"] for opt in p["options"]],
                      format_func=lambda x: labels[x], key=f"quiz_{p['id']}", index=None)
    if st.button("Submit answer", type="primary", disabled=choice is None):
        fb = q.submit_answer(choice)
        ss.quiz_feedback = {"prompt": p, "chosen": choice, "correct": fb["correct"],
                            "correct_option_id": fb["correct_option_id"],
                            "explanation": fb["explanation"]}
        ss.quiz_phase = "review"
        st.rerun()


# --------------------------------------------------------------------------
# Router
# --------------------------------------------------------------------------

{"title": screen_title, "choose": screen_choose, "play": screen_play, "results": screen_results,
 "titles": screen_titles, "howto": screen_howto, "quiz": screen_quiz}.get(ss.screen, screen_title)()
