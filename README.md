# Beatzy – Discord Music Bot

**Beatzy** is a self‑hosted, open‑source Discord music bot built with Python, `discord.py`, and `yt‑dlp`.  
It supports YouTube playback, playlists, search, queue management, and advanced features like **loop**, **24/7 mode**, and live progress updates.

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![discord.py](https://img.shields.io/badge/discord.py-2.3.2-blue.svg)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## ✨ Features

- 🎵 Play music from YouTube (URL or search)
- 📜 Playlist support – add entire YouTube playlists
- 🔁 Loop current track (repeat one)
- ⏸️ Pause / Resume
- ⏭️ Skip / ⏹️ Stop
- 📋 Queue management (view, clear, shuffle)
- 🎛️ Interactive control buttons (Play/Pause, Skip, Stop, Queue)
- 🔄 Live progress bar with elapsed time
- 🔇 24/7 mode – bot stays in voice channel even when idle
- 🧹 Purge bot messages
- ℹ️ `/about` – credits, source, website
- 💾 Persistent queue (saved to database)

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10 or higher
- FFmpeg installed on your system
- A Discord Bot Token with proper permissions (see below)

### Installation

```bash
# Clone the repository
git clone https://github.com/Niksun69/beatzy.git
cd beatzy

# Create a virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Configuration

Create a `config.py` file in the project root (or use environment variables):

```python
# config.py
DISCORD_TOKEN = "your_bot_token_here"
DISCORD_ID = 1234567890   # your guild (server) ID
YTDLP_COOKIES = "cookies.txt"   # optional, path to cookies file
```

&gt; **Tip**: Export cookies from your browser (e.g., with a browser extension) and save as `cookies.txt` to avoid 403 errors on YouTube.

### Running the Bot

```bash
python run.py
```

The bot will log in, sync commands, and be ready.

---

## 🎮 Commands

| Command | Description |
|---------|-------------|
| `/play [query]` | Play a track, playlist, or resume the queue |
| `/pause` | Pause the current track |
| `/resume` | Resume playback |
| `/skip` | Skip the current track |
| `/stop` | Stop playback and disconnect (keeps queue) |
| `/leave` | Disconnect but preserve the queue |
| `/queue` | Show the current queue |
| `/clear` | Clear the queue |
| `/shuffle` | Shuffle the queue |
| `/now` | Show current track with progress |
| `/loop` | Toggle loop mode (repeat current track) |
| `/247` | Toggle 24/7 mode (stay in voice) |
| `/purge [count]` | Delete bot messages in the channel |
| `/about` | Information about the bot |
| `/help` | Show help menu |

---

## 🔧 Permissions

When inviting the bot, ensure you grant:

- **OAuth2 Scopes**: `bot`, `applications.commands`
- **Text Permissions**: `Send Messages`, `Read Message History`
- **Voice Permissions**: `Connect`, `Speak`, `Use Voice Activity`
- **Gateway Intents**: `Message Content Intent` (if using prefix commands), `Server Members Intent`

---

## 📦 Dependencies

- [discord.py](https://github.com/Rapptz/discord.py) – Discord API wrapper
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) – YouTube downloading and extraction
- [aiohttp](https://docs.aiohttp.org/) – async HTTP requests
- [FFmpeg](https://ffmpeg.org/) – audio processing (must be installed separately)

---

## 🤝 Contributing

Contributions are welcome! Feel free to open issues or pull requests.

---

## 🙏 Credits

- **Developer**: [Nikola](https://artisticcode.dev)
- **Website**: [artisticcode.dev](https://artisticcode.dev)
- **Source**: [GitHub](https://github.com/Niksun69/beatzy)

---

## 📄 License

This project is licensed under the MIT License – see the [LICENSE](LICENSE) file for details.

---

**Beatzy** – your personal DJ on Discord. 🎧