import os
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN         = os.getenv("DISCORD_TOKEN")
DISCORD_ID            = os.getenv("DISCORD_ID")
YTDLP_COOKIES         = os.getenv("YTDLP_COOKIES", "./cookies.txt")
DB_PATH               = os.getenv("DB_PATH", "./data/queues.db")
SPOTIFY_CLIENT_ID     = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
RIOT_API_KEY          = os.getenv("RIOT_API_KEY")
DEFAULT_REGION        = os.getenv("DEFAULT_REGION", "eun1")

if not DISCORD_TOKEN:
    raise ValueError("DISCORD_TOKEN not set in .env")