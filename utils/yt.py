import os
import re
import subprocess

import yt_dlp
from yt_dlp.cookies import CookieLoadError


# ============================================================
# CONSTANTS
# ============================================================

YOUTUBE_URL_RE = re.compile(
    r"^https?://",
    re.IGNORECASE,
)

VIDEO_ID_RE = re.compile(
    r"^[A-Za-z0-9_-]{11}$"
)


# ============================================================
# URL HELPERS
# ============================================================

def is_url(text):
    """
    Return True when text looks like an HTTP/HTTPS URL.
    """

    if not text:
        return False

    return YOUTUBE_URL_RE.match(
        text.strip()
    ) is not None


def is_valid_video_id(video_id):
    """
    Validate a YouTube video ID.
    """

    if not video_id:
        return False

    return VIDEO_ID_RE.match(
        video_id.strip()
    ) is not None


# ============================================================
# YT-DLP OPTIONS
# ============================================================

def _build_ydl_options(
    cookies=None,
    browser=None,
):
    """
    Build yt-dlp options optimized for music extraction.

    We prefer Opus because Discord can use Opus directly,
    avoiding an unnecessary decode/re-encode step in many cases.
    """

    ydl_opts = {
        # ----------------------------------------------------
        # AUDIO FORMAT
        # ----------------------------------------------------
        
        "format": (
            "bestaudio[acodec=opus]/"
            "bestaudio/"
            "best"
        ),

        # ----------------------------------------------------
        # OUTPUT
        # ----------------------------------------------------

        "quiet": True,
        "no_warnings": True,
        "noprogress": True,

        # We only need metadata + a direct stream URL.
        "skip_download": True,

        # ----------------------------------------------------
        # NETWORK RETRIES
        # ----------------------------------------------------

        "retries": 20,
        "fragment_retries": 20,
        "file_access_retries": 10,

        # Wait between retries.
        "retry_sleep_functions": {
            "http": lambda n: min(
                1 + n,
                5,
            ),
            "fragment": lambda n: min(
                1 + n,
                5,
            ),
        },

        # ----------------------------------------------------
        # NETWORK / HTTP
        # ----------------------------------------------------

        "socket_timeout": 30,

        # Don't request gigantic HTTP chunks.
        #
        # This is particularly useful with YouTube because
        # very large chunks can be throttled.
        "http_chunk_size": 5 * 1024 * 1024,

        # ----------------------------------------------------
        # YOUTUBE
        # ----------------------------------------------------

        "extractor_retries": 5,

        # Prefer clients which normally provide good audio
        # formats while avoiding unnecessary browser emulation.
        "extractor_args": {
            "youtube": {
                "player_client": [
                    "android",
                    "web",
                ],
            }
        },

        # ----------------------------------------------------
        # GEO / CERTIFICATE / NETWORK SAFETY
        # ----------------------------------------------------

        "nocheckcertificate": False,

        # ----------------------------------------------------
        # METADATA
        # ----------------------------------------------------

        "writesubtitles": False,
        "writeautomaticsub": False,
        "writethumbnail": False,

        # Don't fetch comments, likes, etc.
        "getcomments": False,

        # ----------------------------------------------------
        # PLAYLIST
        # ----------------------------------------------------

        "noplaylist": False,
    }

    # --------------------------------------------------------
    # Cookie file
    # --------------------------------------------------------

    if cookies:
        if os.path.exists(cookies):
            ydl_opts["cookiefile"] = cookies

    # --------------------------------------------------------
    # Browser cookies
    # --------------------------------------------------------

    if browser:
        ydl_opts["cookiesfrombrowser"] = (
            browser,
        )

    return ydl_opts


# ============================================================
# INFO NORMALIZATION
# ============================================================

def _normalize_info(info):
    """
    Normalize yt-dlp output so the rest of the bot receives
    consistent metadata.
    """

    if not info:
        return None

    # --------------------------------------------------------
    # Search result
    # --------------------------------------------------------

    if (
        info.get("_type") == "playlist"
        and info.get("entries")
    ):
        entries = [
            entry
            for entry in info["entries"]
            if entry
        ]

        if not entries:
            return None

        info = entries[0]

    # --------------------------------------------------------
    # Basic metadata
    # --------------------------------------------------------

    title = info.get(
        "title"
    ) or "Unknown Track"

    thumbnail = info.get(
        "thumbnail"
    )

    duration = info.get(
        "duration"
    ) or 0

    webpage_url = (
        info.get("webpage_url")
        or info.get("original_url")
        or info.get("url")
    )

    # --------------------------------------------------------
    # Artist / uploader
    # --------------------------------------------------------

    artist = (
        info.get("artist")
        or info.get("creator")
        or info.get("uploader")
        or info.get("channel")
    )

    # --------------------------------------------------------
    # Direct media URL
    # --------------------------------------------------------

    direct_url = info.get(
        "url"
    )

    # --------------------------------------------------------
    # Selected format metadata
    # --------------------------------------------------------

    acodec = info.get(
        "acodec"
    )

    ext = info.get(
        "ext"
    )

    abr = info.get(
        "abr"
    )

    asr = info.get(
        "asr"
    )

    # --------------------------------------------------------
    # Return normalized object
    # --------------------------------------------------------

    info["title"] = title
    info["thumbnail"] = thumbnail
    info["duration"] = duration
    info["webpage_url"] = webpage_url
    info["artist"] = artist
    info["url"] = direct_url
    info["acodec"] = acodec
    info["ext"] = ext
    info["abr"] = abr
    info["asr"] = asr

    return info


# ============================================================
# EXTRACT INFO
# ============================================================

def extract_info(
    url,
    cookies=None,
    browser=None,
):
    """
    Extract audio information from:

        - YouTube URL
        - YouTube search query

    Returns yt-dlp's information dictionary with normalized
    fields.

    The direct `url` returned here is the media URL that
    FFmpeg will consume.
    """

    if not url:
        return None

    url = url.strip()

    # --------------------------------------------------------
    # Search
    # --------------------------------------------------------

    if not is_url(url):
        url = f"ytsearch1:{url}"

    # --------------------------------------------------------
    # Build options
    # --------------------------------------------------------

    ydl_opts = _build_ydl_options(
        cookies=cookies,
        browser=browser,
    )

    # --------------------------------------------------------
    # Extraction
    # --------------------------------------------------------

    try:

        with yt_dlp.YoutubeDL(
            ydl_opts
        ) as ydl:

            info = ydl.extract_info(
                url,
                download=False,
            )

            return _normalize_info(
                info
            )

    # --------------------------------------------------------
    # Cookie failure
    # --------------------------------------------------------

    except CookieLoadError:

        # Retry without cookies.

        if (
            "cookiefile" in ydl_opts
            or "cookiesfrombrowser" in ydl_opts
        ):

            ydl_opts.pop(
                "cookiefile",
                None,
            )

            ydl_opts.pop(
                "cookiesfrombrowser",
                None,
            )

            with yt_dlp.YoutubeDL(
                ydl_opts
            ) as ydl:

                info = ydl.extract_info(
                    url,
                    download=False,
                )

                return _normalize_info(
                    info
                )

        raise

    # --------------------------------------------------------
    # yt-dlp errors
    # --------------------------------------------------------

    except yt_dlp.utils.DownloadError as e:

        print(
            f"[yt-dlp] Failed to extract "
            f"'{url}': {e}"
        )

        return None

    # --------------------------------------------------------
    # Unexpected errors
    # --------------------------------------------------------

    except Exception as e:

        print(
            f"[yt-dlp] Unexpected extraction "
            f"error: {e}"
        )

        return None


# ============================================================
# PLAYLIST IDS
# ============================================================

def get_playlist_ids(
    url,
    cookies=None,
    browser=None,
):
    """
    Extract YouTube video IDs from a playlist.

    Uses yt-dlp's Python API instead of spawning a second
    yt-dlp process where possible.

    Falls back to the command line if necessary.
    """

    if not url:
        return []

    # ========================================================
    # PYTHON API
    # ========================================================

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,

        "extract_flat": True,

        "skip_download": True,

        "ignoreerrors": True,

        "playlistend": None,

        "retries": 5,
        "fragment_retries": 5,

        "socket_timeout": 20,

        "extractor_retries": 5,

        "extractor_args": {
            "youtube": {
                "player_client": [
                    "android",
                    "web",
                ],
            }
        },
    }

    # --------------------------------------------------------
    # Cookies
    # --------------------------------------------------------

    if cookies and os.path.exists(cookies):
        ydl_opts["cookiefile"] = cookies

    if browser:
        ydl_opts["cookiesfrombrowser"] = (
            browser,
        )

    try:

        with yt_dlp.YoutubeDL(
            ydl_opts
        ) as ydl:

            info = ydl.extract_info(
                url,
                download=False,
            )

            if not info:
                return []

            entries = info.get(
                "entries",
                [],
            )

            video_ids = []

            for entry in entries:

                if not entry:
                    continue

                video_id = (
                    entry.get("id")
                )

                if is_valid_video_id(
                    video_id
                ):
                    video_ids.append(
                        video_id
                    )

            if video_ids:
                return video_ids

    except CookieLoadError:

        # Retry without cookies.
        return get_playlist_ids(
            url,
            cookies=None,
            browser=None,
        )

    except Exception as e:

        print(
            f"[yt-dlp] Python playlist "
            f"extraction failed: {e}"
        )

    # ========================================================
    # CLI FALLBACK
    # ========================================================

    return _get_playlist_ids_cli(
        url,
        cookies=cookies,
        browser=browser,
    )


# ============================================================
# CLI PLAYLIST FALLBACK
# ============================================================

def _get_playlist_ids_cli(
    url,
    cookies=None,
    browser=None,
):
    """
    Command-line fallback for playlist extraction.
    """

    cmd = [
        "yt-dlp",
        "--flat-playlist",
        "--skip-download",
        "--print",
        "%(id)s",
    ]

    # --------------------------------------------------------
    # Cookies
    # --------------------------------------------------------

    if cookies and os.path.exists(cookies):

        cmd.extend(
            [
                "--cookies",
                cookies,
            ]
        )

    elif browser:

        cmd.extend(
            [
                "--cookies-from-browser",
                browser,
            ]
        )

    # --------------------------------------------------------
    # Network settings
    # --------------------------------------------------------

    cmd.extend(
        [
            "--retries",
            "5",
            "--extractor-retries",
            "5",
            "--socket-timeout",
            "20",
        ]
    )

    # --------------------------------------------------------
    # Playlist URL
    # --------------------------------------------------------

    cmd.append(url)

    try:

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
        )

        # ----------------------------------------------------
        # Failed with cookies
        # ----------------------------------------------------

        if result.returncode != 0:

            if cookies or browser:

                return _get_playlist_ids_cli(
                    url,
                    cookies=None,
                    browser=None,
                )

            print(
                "[yt-dlp] Playlist command failed:\n"
                f"{result.stderr.strip()}"
            )

            return []

        # ----------------------------------------------------
        # Parse IDs
        # ----------------------------------------------------

        video_ids = []

        for line in result.stdout.splitlines():

            line = line.strip()

            if is_valid_video_id(
                line
            ):
                video_ids.append(
                    line
                )

        return video_ids

    except subprocess.TimeoutExpired:

        print(
            "[yt-dlp] Playlist extraction timed out."
        )

        return []

    except FileNotFoundError:

        print(
            "[yt-dlp] yt-dlp executable "
            "was not found."
        )

        return []

    except Exception as e:

        print(
            f"[yt-dlp] CLI playlist "
            f"extraction failed: {e}"
        )

        return []

# ============================================================
# PLAYLIST ENTRIES (with titles & durations)
# ============================================================
def get_playlist_entries(url, cookies=None, browser=None):
    if not url:
        return []

    cmd = [
        "yt-dlp",
        "--flat-playlist",
        "--skip-download",
        "--print", "%(id)s",
        "--print", "%(title)s",
        "--print", "%(duration)s",
        "--ignore-errors",
    ]
    if cookies and os.path.exists(cookies):
        cmd.extend(["--cookies", cookies])
    elif browser:
        cmd.extend(["--cookies-from-browser", browser])

    cmd.extend(["--retries", "5", "--socket-timeout", "30", url])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            print(f"[yt-dlp CLI] stderr: {result.stderr.strip()}")
            return []

        lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
        entries = []
        for i in range(0, len(lines), 3):
            if i+2 >= len(lines):
                break
            vid = lines[i]
            title = lines[i+1] or "Unknown Title"
            dur_str = lines[i+2]
            duration = int(dur_str) if dur_str.isdigit() else None
            if is_valid_video_id(vid):
                entries.append({"id": vid, "title": title, "duration": duration})
        return entries
    except Exception as e:
        print(f"[yt-dlp CLI] failed: {e}")
        return []


def _get_playlist_entries_cli(url, cookies=None, browser=None):
    """
    Command-line fallback for playlist entries (returns dicts with id, title, duration).
    """
    cmd = [
        "yt-dlp",
        "--flat-playlist",
        "--skip-download",
        "--print",
        "%(id)s",
        "--print",
        "%(title)s",
        "--print",
        "%(duration)s",
    ]

    if cookies and os.path.exists(cookies):
        cmd.extend(["--cookies", cookies])
    elif browser:
        cmd.extend(["--cookies-from-browser", browser])

    cmd.extend([
        "--retries", "5",
        "--extractor-retries", "5",
        "--socket-timeout", "20",
        url
    ])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode != 0:
            if cookies or browser:
                return _get_playlist_entries_cli(url, cookies=None, browser=None)
            print(f"[yt-dlp] Playlist command failed:\n{result.stderr.strip()}")
            return []

        # Output has three lines per entry: id, title, duration
        lines = result.stdout.strip().splitlines()
        entries = []
        for i in range(0, len(lines), 3):
            if i+2 >= len(lines):
                break
            vid = lines[i].strip()
            title = lines[i+1].strip() or "Unknown Title"
            dur_str = lines[i+2].strip()
            duration = int(dur_str) if dur_str.isdigit() else None
            if is_valid_video_id(vid):
                entries.append({"id": vid, "title": title, "duration": duration})
        return entries

    except Exception as e:
        print(f"[yt-dlp] CLI playlist entries failed: {e}")
        return []