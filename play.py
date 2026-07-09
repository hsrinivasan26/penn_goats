"""Terminal game loop for Penn Goats -- play the engine before any UI exists.

    python play.py                    # interactive, Path A, seed 0
    python play.py --path B --seed 7  # interactive, Path B
    python play.py --auto 60          # headless: auto-play up to 60 turns, print a summary
"""

import argparse
import config
from game.state import new_game
from game.rng import SeededRNG
from game import choices
from game.engine import run_turn
from game.enums import GameOver

ASSET_CLASSES = ["riskfree", "index", "growth", "crypto"]
GAME_OVER_BLURB = {
    GameOver.WIN: "YOU WIN -- you reached a real safety buffer. That's the goal: not living paycheck to paycheck.",
    GameOver.BANKRUPTCY: "BANKRUPT -- you couldn't cover essentials several months running. That shortfall spiral is exactly what this game is about avoiding.",
    GameOver.BURNOUT: "BURNOUT -- happiness hit zero. Money isn't everything; you have to enjoy some of it.",
    GameOver.TIMEOUT: "TIME'S UP -- you survived, but didn't reach the buffer target.",
}


def money(n):
    return f"-${abs(n):,}" if n < 0 else f"${n:,}"


def _ask(prompt):
    """input() that treats EOF/blank as 'done' instead of crashing."""
    try:
        return input(prompt).strip()
    except EOFError:
        return ""


def _ask_int(prompt):
    raw = _ask(prompt)
    try:
        return int(raw)
    except ValueError:
        return None


# --------------------------------------------------------------------------
# Display
# --------------------------------------------------------------------------

def print_turn_story(state):
    print("\n" + "=" * 56)
    print(f" MONTH {state.turn}   (goal: net worth {money(state.target)} by month {config.TURN_LIMIT})")
    print("=" * 56)

    stub = state._paystub
    if stub and stub["gross"] > 0:
        print(" Paycheck")
        print(f"   gross            {money(stub['gross'])}")
        print(f"   - federal tax    {money(stub['federal'])}")
        print(f"   - state tax      {money(stub['state'])}")
        print(f"   - FICA           {money(stub['fica'])}")
        print(f"   = take-home      {money(stub['net'])}   <- the number that actually lands")
    else:
        print(" No paycheck this month (unemployed).")

    if state._tax:
        t = state._tax
        print(f" Year-end taxes: bill {money(t['tax_bill'])}, paid {money(t['paid'])}, "
              f"still owed {money(t['still_owed'])}")

    ev = state._event
    if ev:
        detail = money(ev["cash_delta"]) if ev["cash_delta"] else (
            f"{ev['happiness_delta']:+d} mood" if ev["happiness_delta"] else "no cash effect")
        print(f" Life happens: {ev['label']} ({detail})")


def print_status(state):
    debts = sum(l["principal"] for l in state.liabilities.values() if l) + state.tax_owed
    print("-" * 56)
    print(f" cash {money(state.cash)} | invest {money(state.investments_total())} | "
          f"debt {money(debts)} | net worth {money(state.net_worth())}")
    print(f" happiness {state.happiness}/100 | gross/mo {money(state.gross_month)} | "
          f"housing {state.housing.value}")


# --------------------------------------------------------------------------
# Interactive Phase-6 menu
# --------------------------------------------------------------------------

def interactive_actions(state):
    print_turn_story(state)
    while True:
        print_status(state)
        print(" Your move:  [1] invest  [2] sell  [3] leisure  [4] pay debt  "
              "[5] big move  [6] end month")
        choice = _ask(" > ")
        if choice in ("6", ""):
            return
        elif choice == "1":
            cls = _ask(f"   which asset {ASSET_CLASSES}? ")
            amt = _ask_int("   how much? ")
            ok = amt is not None and choices.invest(state, amt, cls)
            print("   done." if ok else "   (can't do that -- checked cash & asset name)")
        elif choice == "2":
            cls = _ask(f"   sell which asset {ASSET_CLASSES}? ")
            amt = _ask_int("   how much? ")
            ok = amt is not None and choices.sell(state, amt, cls)
            print("   done." if ok else "   (can't do that -- you don't hold that much)")
        elif choice == "3":
            amt = _ask_int("   spend how much on leisure? ")
            ok = amt is not None and choices.leisure(state, amt)
            print("   enjoy." if ok else "   (not enough cash)")
        elif choice == "4":
            slot = _ask("   pay which debt [student/credit_card/mortgage]? ")
            amt = _ask_int("   how much? ")
            ok = amt is not None and choices.pay_debt(state, amt, slot)
            print("   done." if ok else "   (no such debt or not enough cash)")
        elif choice == "5":
            _big_move_menu(state)
        else:
            print("   (didn't recognize that)")


def _big_move_menu(state):
    print("   big moves: [a] buy house  [b] go to school  [c] change job  "
          "[d] buy car (cash)  [e] cancel")
    pick = _ask("   > ")
    if pick == "a":
        price = _ask_int("   home price? ")
        down = _ask_int("   down payment? ")
        ok = None not in (price, down) and choices.buy_house(state, price, down)
        print("   keys in hand!" if ok else "   (can't afford that down payment)")
    elif pick == "b":
        cost = _ask_int("   tuition (taken as a student loan)? ")
        ok = cost is not None and choices.go_to_school(state, cost)
        print("   enrolled." if ok else "   (invalid amount)")
    elif pick == "c":
        gross = _ask_int("   new monthly gross? ")
        ok = gross is not None and choices.change_job(state, gross)
        print("   new job!" if ok else "   (invalid amount)")
    elif pick == "d":
        price = _ask_int("   car price (cash)? ")
        ok = price is not None and choices.buy_car(state, price)
        print("   vroom." if ok else "   (not enough cash)")


# --------------------------------------------------------------------------
# Auto (headless) strategy for balance-testing
# --------------------------------------------------------------------------

def auto_strategy(state):
    choices.leisure(state, 60)                       # a little fun every month
    if state.cash > 1500:                             # invest surplus into the index fund
        choices.invest(state, state.cash - 1000, "index")


# --------------------------------------------------------------------------
# Runners
# --------------------------------------------------------------------------

def play_interactive(path, seed):
    state = new_game(path, seed=seed)
    rng = SeededRNG(seed)
    print(f"Penn Goats -- Path {path}, seed {seed}. Survive to the buffer. Ctrl-C to quit.")
    while not state.game_over:
        before = state.happiness
        run_turn(state, rng, choose_actions=interactive_actions)
        delta = state.happiness - before
        if state._milestone:
            print(f" * milestone: {state._milestone['label']} (+{state._milestone['bonus']} happy)")
        print(f" end of month: happiness {state.happiness}/100 ({delta:+d})")
    print("\n" + GAME_OVER_BLURB.get(state.game_over, str(state.game_over)))
    print(f"Final net worth: {money(state.net_worth())} after {state.turn} months.")


def play_auto(path, seed, turns):
    state = new_game(path, seed=seed)
    rng = SeededRNG(seed)
    print(f"AUTO  Path {path}, seed {seed}  (win target {money(state.target)})")
    print(f"{'mo':>3} {'cash':>8} {'net_worth':>10} {'happy':>6}  event")
    for _ in range(turns):
        run_turn(state, rng, choose_actions=auto_strategy)
        snap = state.history[-1]
        print(f"{snap['turn']:>3} {snap['cash']:>8} {snap['net_worth']:>10} "
              f"{snap['happiness']:>6}  {snap['event'] or ''}")
        if state.game_over:
            break
    outcome = state.game_over.value if state.game_over else "still going"
    print(f"\nResult: {outcome} | "
          f"net worth {money(state.net_worth())} | happiness {state.happiness}/100")


def main():
    ap = argparse.ArgumentParser(description="Play the Penn Goats engine in the terminal.")
    ap.add_argument("--path", choices=["A", "B"], default="A")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--auto", type=int, metavar="TURNS",
                    help="headless: auto-play this many turns and print a summary")
    args = ap.parse_args()

    if args.auto:
        play_auto(args.path, args.seed, args.auto)
    else:
        play_interactive(args.path, args.seed)


if __name__ == "__main__":
    main()
