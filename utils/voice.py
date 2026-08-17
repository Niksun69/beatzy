import time
from utils.db import save_queue, load_all_queues, init_db

queues = {}             # guild_id -> list of track dicts
current_tracks = {}     # guild_id -> dict with metadata of current playing track

def load_queues_from_db():
    global queues
    init_db()
    queues = load_all_queues()
    # Ensure every queue is a list
    for gid in list(queues.keys()):
        if not isinstance(queues[gid], list):
            queues[gid] = []

def get_queue(guild_id):
    if guild_id not in queues:
        queues[guild_id] = []
    return queues[guild_id]

def clear_queue(guild_id):
    if guild_id in queues:
        queues[guild_id] = []

def save_queue_to_db(guild_id):
    """Persist the queue for a guild."""
    save_queue(guild_id, queues.get(guild_id, []))

def set_current_track(guild_id, title, url, thumbnail, duration):
    current_tracks[guild_id] = {
        "title": title,
        "url": url,
        "thumbnail": thumbnail,
        "duration": duration,
        "start_time": time.time()
    }

def get_current_track(guild_id):
    return current_tracks.get(guild_id)