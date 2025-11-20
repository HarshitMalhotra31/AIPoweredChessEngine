# chess_db.py
import sqlite3
import datetime
from typing import Optional, List, Tuple, Dict

DB_FILENAME = "chess_data.db"

CREATE_PLAYERS = """
CREATE TABLE IF NOT EXISTS players (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    wins INTEGER DEFAULT 0,
    losses INTEGER DEFAULT 0,
    draws INTEGER DEFAULT 0,
    created_at TEXT NOT NULL
);
"""

CREATE_GAMES = """
CREATE TABLE IF NOT EXISTS games (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    player_id INTEGER,
    opponent_type TEXT,
    opponent_name TEXT,
    result TEXT,
    moves TEXT,
    ai_depth INTEGER,
    created_at TEXT NOT NULL,
    FOREIGN KEY(player_id) REFERENCES players(id)
);
"""

CREATE_SETTINGS = """
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
);
"""

def get_connection():
    conn = sqlite3.connect(DB_FILENAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(CREATE_PLAYERS)
    cur.execute(CREATE_GAMES)
    cur.execute(CREATE_SETTINGS)
    conn.commit()
    conn.close()

# ---------- Player helpers ----------
def get_player_by_name(name: str) -> Optional[sqlite3.Row]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM players WHERE name = ?", (name,))
    row = cur.fetchone()
    conn.close()
    return row

def create_player(name: str) -> sqlite3.Row:
    conn = get_connection()
    cur = conn.cursor()
    now = datetime.datetime.utcnow().isoformat()
    cur.execute("INSERT OR IGNORE INTO players (name, created_at) VALUES (?, ?)", (name, now))
    conn.commit()
    cur.execute("SELECT * FROM players WHERE name = ?", (name,))
    row = cur.fetchone()
    conn.close()
    return row

def get_or_create_player(name: str) -> sqlite3.Row:
    row = get_player_by_name(name)
    if row:
        return row
    return create_player(name)

def update_player_stats(name: str, result: str):
    """
    result: 'win' (player wins), 'loss' (player loses), 'draw'
    """
    conn = get_connection()
    cur = conn.cursor()
    if result == 'win':
        cur.execute("UPDATE players SET wins = wins + 1 WHERE name = ?", (name,))
    elif result == 'loss':
        cur.execute("UPDATE players SET losses = losses + 1 WHERE name = ?", (name,))
    elif result == 'draw':
        cur.execute("UPDATE players SET draws = draws + 1 WHERE name = ?", (name,))
    conn.commit()
    conn.close()

def get_player_stats(name: str) -> Dict:
    row = get_player_by_name(name)
    if not row:
        return {"name": name, "wins": 0, "losses": 0, "draws": 0, "total": 0, "win_rate": 0.0}
    wins = row["wins"]
    losses = row["losses"]
    draws = row["draws"]
    total = wins + losses + draws
    win_rate = (wins / total * 100.0) if total > 0 else 0.0
    return {"name": row["name"], "wins": wins, "losses": losses, "draws": draws, "total": total, "win_rate": win_rate}

# ---------- Game history ----------
def record_game(player_name: str, opponent_type: str, opponent_name: Optional[str], result: str, moves: str, ai_depth: Optional[int]=None):
    player = get_or_create_player(player_name)
    player_id = player["id"]
    now = datetime.datetime.utcnow().isoformat()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO games (player_id, opponent_type, opponent_name, result, moves, ai_depth, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (player_id, opponent_type, opponent_name or "", result, moves, ai_depth or 0, now))
    conn.commit()
    conn.close()
    # update player totals
    update_player_stats(player_name, result)

def get_recent_games_for_player(name: str, limit: int = 20) -> List[sqlite3.Row]:
    player = get_player_by_name(name)
    if not player:
        return []
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM games WHERE player_id = ? ORDER BY created_at DESC LIMIT ?", (player["id"], limit))
    rows = cur.fetchall()
    conn.close()
    return rows

# ---------- Settings ----------
def set_setting(key: str, value: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value", (key, value))
    conn.commit()
    conn.close()

def get_setting(key: str, default: Optional[str] = None) -> Optional[str]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT value FROM settings WHERE key = ?", (key,))
    row = cur.fetchone()
    conn.close()
    if row:
        return row["value"]
    return default

# ---------- Utility ----------
def list_players(limit: int=50) -> List[sqlite3.Row]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM players ORDER BY wins DESC LIMIT ?", (limit,))
    rows = cur.fetchall()
    conn.close()
    return rows
