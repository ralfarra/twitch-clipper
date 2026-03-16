"""
Polls Twitch for new VODs (recorded/uploaded videos) for a given channel.
Tracks already-processed VODs in a local SQLite database.
"""

import sqlite3
import requests
from twitch_auth import TwitchAuth


DB_PATH = "state.db"


def init_db():
    con = sqlite3.connect(DB_PATH)
    con.execute("""
        CREATE TABLE IF NOT EXISTS processed_vods (
            vod_id TEXT PRIMARY KEY,
            title TEXT,
            created_at TEXT,
            processed_at TEXT DEFAULT (datetime('now'))
        )
    """)
    con.commit()
    con.close()


def is_processed(vod_id: str) -> bool:
    con = sqlite3.connect(DB_PATH)
    row = con.execute("SELECT 1 FROM processed_vods WHERE vod_id = ?", (vod_id,)).fetchone()
    con.close()
    return row is not None


def mark_processed(vod_id: str, title: str, created_at: str):
    con = sqlite3.connect(DB_PATH)
    con.execute(
        "INSERT OR IGNORE INTO processed_vods (vod_id, title, created_at) VALUES (?, ?, ?)",
        (vod_id, title, created_at),
    )
    con.commit()
    con.close()


def get_new_vods(auth: TwitchAuth, channel: str) -> list[dict]:
    """
    Returns list of new (unprocessed) VODs for the channel.
    Each VOD is a dict with keys: id, title, url, created_at, duration.
    """
    # Resolve channel name to user ID
    resp = requests.get(
        f"{auth.API_BASE}/users",
        headers=auth.headers(),
        params={"login": channel},
    )
    resp.raise_for_status()
    users = resp.json().get("data", [])
    if not users:
        raise ValueError(f"Channel '{channel}' not found on Twitch")
    user_id = users[0]["id"]

    # Fetch recent VODs (type=archive = recorded streams)
    resp = requests.get(
        f"{auth.API_BASE}/videos",
        headers=auth.headers(),
        params={"user_id": user_id, "type": "archive", "first": 10},
    )
    resp.raise_for_status()
    vods = resp.json().get("data", [])

    new_vods = [v for v in vods if not is_processed(v["id"])]
    return new_vods
