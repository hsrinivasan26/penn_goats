"""
db.py

Per-player persistence, backed by SQLite. Replaces the single shared
save_game.json file from local testing -- a real website has many
players at once, so each one needs their own saved row, keyed by
player_id, not one file everyone would overwrite.

Swap this file for your real database layer later (Postgres, etc.) --
as long as get_player/save_player/create_player/delete_player keep the
same signatures, nothing in paystub.py or app.py needs to change.
"""

import json
import sqlite3
import uuid

DB_PATH = "game.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Creates the players table if it doesn't already exist."""
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS players (
            player_id TEXT PRIMARY KEY,
            state_json TEXT NOT NULL,
            game_over INTEGER NOT NULL DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()


def create_player(player_state):
    """Inserts a brand-new player and returns the generated player_id."""
    player_id = str(uuid.uuid4())
    conn = get_connection()
    conn.execute(
        "INSERT INTO players (player_id, state_json, game_over) VALUES (?, ?, 0)",
        (player_id, json.dumps(player_state)),
    )
    conn.commit()
    conn.close()
    return player_id


def get_player(player_id):
    """Returns the player's state dict, or None if no such player exists
    or their game has already ended."""
    conn = get_connection()
    row = conn.execute(
        "SELECT state_json, game_over FROM players WHERE player_id = ?",
        (player_id,),
    ).fetchone()
    conn.close()
    if row is None:
        return None
    state = json.loads(row["state_json"])
    state["_game_over"] = bool(row["game_over"])
    return state


def save_player(player_id, player_state):
    """Persists the player's current state. Call this after every phase
    (paycheck, career progression, tax reconciliation, life events)."""
    state_to_save = {k: v for k, v in player_state.items() if k != "_game_over"}
    conn = get_connection()
    conn.execute(
        "UPDATE players SET state_json = ? WHERE player_id = ?",
        (json.dumps(state_to_save), player_id),
    )
    conn.commit()
    conn.close()


def end_game(player_id):
    """Marks a player's game as finished (bankruptcy, happiness hit 0, etc.).
    Keeps the row (useful for stats/history) but flags it so it can't be
    resumed -- swap for a hard delete_player() if you'd rather remove it."""
    conn = get_connection()
    conn.execute(
        "UPDATE players SET game_over = 1 WHERE player_id = ?",
        (player_id,),
    )
    conn.commit()
    conn.close()


def delete_player(player_id):
    """Hard-deletes a player's save entirely."""
    conn = get_connection()
    conn.execute("DELETE FROM players WHERE player_id = ?", (player_id,))
    conn.commit()
    conn.close()
