import os
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
DISCORD_ID    = os.getenv("DISCORD_ID")
YTDLP_COOKIES = os.getenv("YTDLP_COOKIES", "./cookies.txt")
DB_PATH       = os.getenv("DB_PATH", "./data/queues.db")

if not DISCORD_TOKEN:
    raise ValueError("DISCORD_TOKEN not set in .env")