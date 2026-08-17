import sqlite3
import json
import os
from config import DB_PATH


def init_db():
    """Create the queues table if it doesn't exist."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS queues (
            guild_id INTEGER PRIMARY KEY,
            queue_json TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

def save_queue(guild_id, queue):
    """Save a guild's queue to the database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    queue_json = json.dumps(queue)
    cursor.execute('''
        INSERT OR REPLACE INTO queues (guild_id, queue_json)
        VALUES (?, ?)
    ''', (guild_id, queue_json))
    conn.commit()
    conn.close()

def load_all_queues():
    """Load all queues from the database and return as dict {guild_id: list}."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT guild_id, queue_json FROM queues')
    rows = cursor.fetchall()
    conn.close()
    queues = {}
    for guild_id, queue_json in rows:
        try:
            queues[guild_id] = json.loads(queue_json)
        except json.JSONDecodeError:
            queues[guild_id] = []   # fallback to empty
    return queues

def delete_queue(guild_id):
    """Remove a guild's queue from the database (optional)."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM queues WHERE guild_id = ?', (guild_id,))
    conn.commit()
    conn.close()