"""
app.py

Flask routes for the paystub system. Each route:
  1. loads the player's saved state from the database (db.py)
  2. runs the relevant game logic (paystub.py)
  3. saves the updated state back
  4. returns JSON the frontend can render directly (paystub breakdown,
     tax reconciliation, or a life-event popup payload)

Run locally with: python app.py
"""

from flask import Flask, jsonify, request

import db
import economy
import paystub

app = Flask(__name__)
db.init_db()


def player_not_found():
    return jsonify({"error": "No player found with that id, or their game has ended."}), 404


@app.route("/api/new-game", methods=["POST"])
def new_game():
    """Starts a brand-new player. Body: { "employed": true|false } (optional, defaults true)."""
    employed = request.json.get("employed", True) if request.is_json else True
    player = paystub.new_player(employed=employed)
    player_id = db.create_player(player)
    return jsonify({"player_id": player_id, "state": player})


@app.route("/api/player/<player_id>", methods=["GET"])
def get_player(player_id):
    """Returns the player's current state -- e.g. to redraw the UI on page load."""
    player = db.get_player(player_id)
    if player is None:
        return player_not_found()
    return jsonify(player)


@app.route("/api/player/<player_id>/paycheck", methods=["POST"])
def paycheck(player_id):
    """Runs one paycheck. If the player isn't employed, returns employed: false
    so the frontend knows to skip straight to phase 2 -- no paystub to show."""
    player = db.get_player(player_id)
    if player is None:
        return player_not_found()

    stub = paystub.run_paycheck_phase(player)
    if stub is None:
        return jsonify({"employed": False, "message": "Not employed -- skipping to phase 2."})

    db.save_player(player_id, player)
    return jsonify({"employed": True, "paystub": stub})


@app.route("/api/player/<player_id>/career-progression", methods=["POST"])
def career_progression(player_id):
    """Checked once per in-game year: chance of a raise or promotion."""
    player = db.get_player(player_id)
    if player is None:
        return player_not_found()

    result = paystub.run_career_progression(player)
    db.save_player(player_id, player)
    return jsonify(result)


@app.route("/api/player/<player_id>/tax-reconciliation", methods=["POST"])
def tax_reconciliation(player_id):
    """
    Phase 5: annual tax bill. Body (optional):
      { "short_term_gains": 0, "long_term_gains": 0 }
    These should come from whatever tracks realized investment sales
    over the year -- pass 0 if nothing was sold.
    """
    player = db.get_player(player_id)
    if player is None:
        return player_not_found()

    body = request.get_json(silent=True) or {}
    short_term_gains = body.get("short_term_gains", 0.0)
    long_term_gains = body.get("long_term_gains", 0.0)

    result = paystub.run_annual_tax_reconciliation(player, short_term_gains, long_term_gains)
    db.save_player(player_id, player)
    return jsonify(result)


@app.route("/api/player/<player_id>/life-event", methods=["POST"])
def life_event(player_id):
    """Rolls one random life event and applies it. Returns a popup-ready
    notification: {title, message, type, job_lost}."""
    player = db.get_player(player_id)
    if player is None:
        return player_not_found()

    event = paystub.roll_life_event()
    notification = paystub.apply_life_event(player, event)
    db.save_player(player_id, player)
    return jsonify(notification)


@app.route("/api/asset-info", methods=["GET"])
def asset_info():
    """Descriptions of each investable asset class, for the frontend to
    show as tooltips/info popups before the player picks one."""
    return jsonify(economy.get_asset_descriptions())


@app.route("/api/player/<player_id>/invest", methods=["POST"])
def invest(player_id):
    """
    Moves cash into an asset class. Body:
      { "asset_type": "CRYPTO", "amount": 100 }
    This is the ONLY way cash enters an investment -- turn-based rolls
    never add new principal, they only grow/shrink what's already there.
    """
    player = db.get_player(player_id)
    if player is None:
        return player_not_found()

    body = request.get_json(silent=True) or {}
    asset_type = body.get("asset_type")
    amount = body.get("amount")

    try:
        economy.make_investment(player, asset_type, amount)
    except (ValueError, TypeError) as e:
        return jsonify({"error": str(e)}), 400

    db.save_player(player_id, player)
    return jsonify({"cash": player["cash"], "investments": player["investments"]})


@app.route("/api/player/<player_id>/roll-investments", methods=["POST"])
def roll_investments(player_id):
    """Rolls this turn's return for every asset class the player owns.
    Only changes investment amounts -- cash is untouched."""
    player = db.get_player(player_id)
    if player is None:
        return player_not_found()

    result = economy.roll_all_investments(player)
    db.save_player(player_id, player)
    return jsonify(result)


@app.route("/api/player/<player_id>/end-game", methods=["POST"])
def end_game(player_id):
    """Call this once your game-over logic fires (bankruptcy, happiness
    hits 0, etc.) so the save can no longer be resumed."""
    player = db.get_player(player_id)
    if player is None:
        return player_not_found()

    db.end_game(player_id)
    return jsonify({"message": "Game ended.", "final_state": player})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
