import asyncio
import time
from typing import Any, Optional
from urllib.parse import quote

import aiohttp

from config import RIOT_API_KEY, DEFAULT_REGION


PLATFORM_REGIONS = {
    "br1", "eun1", "euw1", "jp1", "kr", "la1", "la2", "na1",
    "oc1", "tr1", "ru", "me1", "sg2", "tw2", "vn2", "ph2",
}

REGION_TO_CLUSTER = {
    "br1": "americas",
    "la1": "americas",
    "la2": "americas",
    "na1": "americas",
    "eun1": "europe",
    "euw1": "europe",
    "tr1": "europe",
    "ru": "europe",
    "me1": "europe",
    "kr": "asia",
    "jp1": "asia",
    "oc1": "sea",
    "ph2": "sea",
    "sg2": "sea",
    "tw2": "sea",
    "vn2": "sea",
}

DD_BASE = "https://ddragon.leagueoflegends.com"
STATIC_TTL = 6 * 3600

_static_cache: dict[str, Any] = {}
_static_cache_time = 0.0

_http_session: Optional[aiohttp.ClientSession] = None
_http_session_lock = asyncio.Lock()


def _clean_string(value: Any) -> Optional[str]:
    """Convert Riot identifiers to strings and reject empty/None values."""
    if value is None:
        return None
    if isinstance(value, bytes):
        try:
            value = value.decode("utf-8")
        except UnicodeDecodeError:
            return None
    value = str(value).strip()
    return value or None


def _encode_path(value: Any) -> str:
    """
    Safely encode a Riot path component.

    The previous version crashed when a value was None because urllib.parse.quote()
    expects a string/bytes. This helper prevents that class of crash.
    """
    value = _clean_string(value)
    if value is None:
        raise ValueError("Cannot encode an empty Riot API path parameter.")
    return quote(value, safe="")


async def get_http_session() -> aiohttp.ClientSession:
    global _http_session

    async with _http_session_lock:
        if _http_session is None or _http_session.closed:
            timeout = aiohttp.ClientTimeout(
                total=25,
                connect=8,
                sock_read=18,
            )
            _http_session = aiohttp.ClientSession(timeout=timeout)

        return _http_session


async def close_http_session() -> None:
    global _http_session

    if _http_session is not None and not _http_session.closed:
        await _http_session.close()

    _http_session = None


def get_region_host(region: str) -> str:
    return f"https://{region.lower()}.api.riotgames.com"


def get_cluster_host(cluster: str) -> str:
    return f"https://{cluster.lower()}.api.riotgames.com"


def get_match_host(region: str) -> str:
    cluster = REGION_TO_CLUSTER.get(region.lower())
    if not cluster:
        raise ValueError(f"Unknown Riot regional routing: {region}")
    return get_cluster_host(cluster)


async def riot_api_request(
    url: str,
    params: Optional[dict[str, Any]] = None,
    *,
    retries: int = 4,
) -> Any:
    if not RIOT_API_KEY:
        return {"error": "RIOT_API_KEY is not set."}

    session = await get_http_session()

    headers = {
        "X-Riot-Token": RIOT_API_KEY,
        "Accept": "application/json",
        "User-Agent": "Discord-LoL-Bot/1.0",
    }

    for attempt in range(retries + 1):
        try:
            async with session.get(
                url,
                headers=headers,
                params=params,
            ) as response:

                if response.status == 200:
                    return await response.json(content_type=None)

                if response.status == 404:
                    return None

                if response.status == 401:
                    return {
                        "error": "Invalid or expired Riot API key (401)."
                    }

                if response.status == 403:
                    return {
                        "error": (
                            "Riot API returned 403 Forbidden. "
                            "Check your API key and routing."
                        )
                    }

                if response.status == 429:
                    retry_after_raw = response.headers.get(
                        "Retry-After",
                        "2",
                    )

                    try:
                        retry_after = float(retry_after_raw)
                    except ValueError:
                        retry_after = 2.0

                    if attempt >= retries:
                        return {
                            "error": (
                                f"Rate limited by Riot (429) after "
                                f"{retries + 1} attempts."
                            )
                        }

                    await asyncio.sleep(min(retry_after, 15))
                    continue

                if response.status in {500, 502, 503, 504}:
                    if attempt < retries:
                        await asyncio.sleep(
                            min(1.5 * (2 ** attempt), 8)
                        )
                        continue

                body = await response.text()

                return {
                    "error": (
                        f"Riot API error {response.status}: "
                        f"{body[:500]}"
                    )
                }

        except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
            if attempt >= retries:
                return {
                    "error": f"Network error talking to Riot API: {exc}"
                }

            await asyncio.sleep(
                min(1.5 * (2 ** attempt), 8)
            )

        except ValueError as exc:
            return {
                "error": f"Invalid Riot API request: {exc}"
            }

    return {"error": "Unknown Riot API failure."}


# ---------------------------------------------------------------------------
# DATA DRAGON
# ---------------------------------------------------------------------------

async def get_latest_ddragon_version() -> str:
    session = await get_http_session()

    try:
        async with session.get(
            f"{DD_BASE}/api/versions.json"
        ) as response:

            if response.status == 200:
                versions = await response.json(
                    content_type=None
                )

                if isinstance(versions, list) and versions:
                    return str(versions[0])

    except (aiohttp.ClientError, asyncio.TimeoutError):
        pass

    # Fallback only if Data Dragon's versions endpoint is temporarily down.
    return "16.9.1"


async def _fetch_json(url: str) -> Any:
    session = await get_http_session()

    try:
        async with session.get(url) as response:
            if response.status == 200:
                return await response.json(content_type=None)
    except (aiohttp.ClientError, asyncio.TimeoutError):
        pass

    return {}


async def get_static_data() -> dict[str, Any]:
    global _static_cache
    global _static_cache_time

    now = time.time()

    if (
        _static_cache
        and now - _static_cache_time < STATIC_TTL
    ):
        return _static_cache

    version = await get_latest_ddragon_version()

    data_url = f"{DD_BASE}/cdn/{version}/data/en_US"

    results = await asyncio.gather(
        _fetch_json(
            f"{data_url}/champion.json"
        ),
        _fetch_json(
            f"{data_url}/item.json"
        ),
        _fetch_json(
            f"{data_url}/summoner.json"
        ),
        _fetch_json(
            f"{data_url}/runesReforged.json"
        ),
        _fetch_json(
            "https://static.developer.riotgames.com/docs/lol/queues.json"
        ),
    )

    champions_raw, items_raw, spells_raw, runes_raw, queues_raw = results

    champion_map: dict[int, dict[str, str]] = {}

    champion_data = (
        champions_raw.get("data", {})
        if isinstance(champions_raw, dict)
        else {}
    )

    for champion_id, champion in champion_data.items():
        try:
            numeric_id = int(champion.get("key"))
        except (TypeError, ValueError):
            continue

        champion_map[numeric_id] = {
            "name": champion.get(
                "name",
                champion_id,
            ),
            "id": champion_id,
            "icon": (
                f"{DD_BASE}/cdn/{version}/img/champion/"
                f"{champion_id}.png"
            ),
        }

    item_map: dict[int, dict[str, str]] = {}

    item_data = (
        items_raw.get("data", {})
        if isinstance(items_raw, dict)
        else {}
    )

    for item_id, item in item_data.items():
        try:
            numeric_id = int(item_id)
        except (TypeError, ValueError):
            continue

        if numeric_id <= 0:
            continue

        item_map[numeric_id] = {
            "name": item.get(
                "name",
                f"Item {numeric_id}",
            ),
            "icon": (
                f"{DD_BASE}/cdn/{version}/img/item/"
                f"{numeric_id}.png"
            ),
        }

    spell_map: dict[int, str] = {}

    spell_data = (
        spells_raw.get("data", {})
        if isinstance(spells_raw, dict)
        else {}
    )

    for spell_key, spell in spell_data.items():
        try:
            numeric_id = int(spell.get("key"))
        except (TypeError, ValueError):
            continue

        if numeric_id:
            spell_map[numeric_id] = spell.get(
                "name",
                spell_key,
            )

    queue_map: dict[int, str] = {}

    if isinstance(queues_raw, list):
        for queue in queues_raw:
            if not isinstance(queue, dict):
                continue

            queue_id = queue.get("queueId")

            if queue_id is None:
                continue

            try:
                queue_id = int(queue_id)
            except (TypeError, ValueError):
                continue

            queue_map[queue_id] = (
                queue.get("description")
                or queue.get("map")
                or "Unknown"
            )

    _static_cache = {
        "version": version,
        "champions": champion_map,
        "items": item_map,
        "spells": spell_map,
        "runes": (
            runes_raw
            if isinstance(runes_raw, list)
            else []
        ),
        "queues": queue_map,
    }

    _static_cache_time = now

    return _static_cache


async def get_champion_map():
    data = await get_static_data()
    return data.get("champions", {})


# ---------------------------------------------------------------------------
# ACCOUNT / SUMMONER
# ---------------------------------------------------------------------------

async def get_account_by_riot_id(
    game_name: str,
    tag_line: str,
    cluster: str,
) -> Any:

    game_name = _clean_string(game_name)
    tag_line = _clean_string(tag_line)
    cluster = _clean_string(cluster)

    if not game_name or not tag_line:
        return {
            "error": "Riot ID game name and tag line cannot be empty."
        }

    if not cluster:
        return {
            "error": "Riot regional cluster is missing."
        }

    url = (
        f"{get_cluster_host(cluster)}"
        f"/riot/account/v1/accounts/by-riot-id/"
        f"{_encode_path(game_name)}/"
        f"{_encode_path(tag_line)}"
    )

    return await riot_api_request(url)


async def get_account_by_puuid(
    puuid: str,
    cluster: str,
) -> Any:

    try:
        encoded = _encode_path(puuid)
    except ValueError as exc:
        return {"error": str(exc)}

    url = (
        f"{get_cluster_host(cluster)}"
        f"/riot/account/v1/accounts/by-puuid/{encoded}"
    )

    return await riot_api_request(url)


async def get_summoner_by_puuid(
    puuid: str,
    region: str,
) -> Any:

    try:
        encoded = _encode_path(puuid)
    except ValueError as exc:
        return {"error": str(exc)}

    url = (
        f"{get_region_host(region)}"
        f"/lol/summoner/v4/summoners/by-puuid/{encoded}"
    )

    return await riot_api_request(url)


async def get_summoner_data(
    query: str,
    region: str = DEFAULT_REGION,
) -> Any:

    region = _clean_string(region)

    if not region:
        return {"error": "Region is empty."}

    region = region.lower()

    if region not in PLATFORM_REGIONS:
        return {
            "error": (
                f"Unknown League region '{region}'."
            )
        }

    query = _clean_string(query)

    if not query or query.count("#") != 1:
        return {
            "error": (
                "Use Riot ID format: "
                "gameName#tagLine."
            )
        }

    game_name, tag_line = query.split("#", 1)

    game_name = _clean_string(game_name)
    tag_line = _clean_string(tag_line)

    if not game_name or not tag_line:
        return {
            "error": "Riot ID cannot contain an empty part."
        }

    cluster = REGION_TO_CLUSTER.get(region)

    if not cluster:
        return {
            "error": (
                f"No regional routing exists for {region}."
            )
        }

    account = await get_account_by_riot_id(
        game_name,
        tag_line,
        cluster,
    )

    if not account:
        return {
            "error": (
                f"{game_name}#{tag_line} was not found."
            )
        }

    if is_error(account):
        return account

    puuid = _clean_string(account.get("puuid"))

    if not puuid:
        return {
            "error": (
                "Riot account was found, but Riot did not "
                "return a PUUID."
            )
        }

    summoner = await get_summoner_by_puuid(
        puuid,
        region,
    )

    if not summoner:
        return {
            "error": (
                f"Riot account exists, but no League "
                f"summoner was found on {region.upper()}."
            )
        }

    if is_error(summoner):
        return summoner

    # IMPORTANT:
    # Some Riot responses no longer contain "id".
    # PUUID is the stable identifier we use throughout the bot.
    summoner["_puuid"] = puuid
    summoner["_gameName"] = account.get(
        "gameName",
        game_name,
    )
    summoner["_tagLine"] = account.get(
        "tagLine",
        tag_line,
    )
    summoner["_account"] = account

    return summoner


# ---------------------------------------------------------------------------
# RANKED - PUUID BASED
# ---------------------------------------------------------------------------

async def get_ranked_entries_by_puuid(
    puuid: str,
    region: str = DEFAULT_REGION,
) -> Any:

    try:
        encoded = _encode_path(puuid)
    except ValueError as exc:
        return {"error": str(exc)}

    url = (
        f"{get_region_host(region)}"
        f"/lol/league/v4/entries/by-puuid/{encoded}"
    )

    return await riot_api_request(url)


# Backwards-compatible wrapper.
async def get_ranked_entries(
    summoner_id: str,
    region: str = DEFAULT_REGION,
) -> Any:
    # Kept for old code. New code should use get_ranked_entries_by_puuid().
    return {
        "error": (
            "get_ranked_entries() requires the old summoner ID endpoint. "
            "Use get_ranked_entries_by_puuid() instead."
        )
    }


# ---------------------------------------------------------------------------
# MASTERY - PUUID BASED
# ---------------------------------------------------------------------------

async def get_top_champion_masteries_by_puuid(
    puuid: str,
    count: int = 10,
    region: str = DEFAULT_REGION,
) -> Any:

    try:
        encoded = _encode_path(puuid)
    except ValueError as exc:
        return {"error": str(exc)}

    url = (
        f"{get_region_host(region)}"
        f"/lol/champion-mastery/v4/champion-masteries/"
        f"by-puuid/{encoded}/top"
    )

    return await riot_api_request(
        url,
        params={
            "count": min(
                max(int(count), 1),
                100,
            )
        },
    )


async def get_all_champion_masteries_by_puuid(
    puuid: str,
    region: str = DEFAULT_REGION,
) -> Any:

    try:
        encoded = _encode_path(puuid)
    except ValueError as exc:
        return {"error": str(exc)}

    url = (
        f"{get_region_host(region)}"
        f"/lol/champion-mastery/v4/champion-masteries/"
        f"by-puuid/{encoded}"
    )

    return await riot_api_request(url)


# Backwards-compatible mastery wrappers.
async def get_top_champion_masteries(
    summoner_id: str,
    count: int = 10,
    region: str = DEFAULT_REGION,
) -> Any:
    return {
        "error": (
            "Use get_top_champion_masteries_by_puuid() "
            "instead of the old summoner-ID endpoint."
        )
    }


async def get_all_champion_masteries(
    summoner_id: str,
    region: str = DEFAULT_REGION,
) -> Any:
    return {
        "error": (
            "Use get_all_champion_masteries_by_puuid() "
            "instead of the old summoner-ID endpoint."
        )
    }


# ---------------------------------------------------------------------------
# MATCH V5
# ---------------------------------------------------------------------------

async def get_match_ids_by_puuid(
    puuid: str,
    region: str,
    count: int = 20,
    queue: Optional[int] = None,
    start: Optional[int] = None,
    end: Optional[int] = None,
) -> Any:

    try:
        encoded = _encode_path(puuid)
    except ValueError as exc:
        return {"error": str(exc)}

    url = (
        f"{get_match_host(region)}"
        f"/lol/match/v5/matches/by-puuid/{encoded}/ids"
    )

    params: dict[str, Any] = {
        "count": min(
            max(int(count), 1),
            100,
        )
    }

    if queue is not None:
        params["queue"] = queue

    if start is not None:
        params["start"] = max(int(start), 0)

    if end is not None:
        params["end"] = max(int(end), 0)

    return await riot_api_request(
        url,
        params=params,
    )


async def get_match_details(
    match_id: str,
    region: str,
) -> Any:

    try:
        encoded = _encode_path(match_id)
    except ValueError as exc:
        return {"error": str(exc)}

    url = (
        f"{get_match_host(region)}"
        f"/lol/match/v5/matches/{encoded}"
    )

    return await riot_api_request(url)


async def get_match_timeline(
    match_id: str,
    region: str,
) -> Any:

    try:
        encoded = _encode_path(match_id)
    except ValueError as exc:
        return {"error": str(exc)}

    url = (
        f"{get_match_host(region)}"
        f"/lol/match/v5/matches/{encoded}/timeline"
    )

    return await riot_api_request(url)


# ---------------------------------------------------------------------------
# SPECTATOR
# ---------------------------------------------------------------------------

async def get_active_game(
    puuid: str,
    region: str,
) -> Any:

    # Current implementation is intentionally PUUID based.
    # Most importantly, do not call quote(None).
    try:
        encoded = _encode_path(puuid)
    except ValueError as exc:
        return {"error": str(exc)}

    url = (
        f"{get_region_host(region)}"
        f"/lol/spectator/v5/active-games/by-summoner/"
        f"{encoded}"
    )

    return await riot_api_request(url)


async def get_featured_games(
    region: str,
) -> Any:

    url = (
        f"{get_region_host(region)}"
        f"/lol/spectator/v5/featured-games"
    )

    return await riot_api_request(url)


# ---------------------------------------------------------------------------
# CHALLENGES
# ---------------------------------------------------------------------------

async def get_challenges(
    puuid: str,
    region: str,
) -> Any:

    try:
        encoded = _encode_path(puuid)
    except ValueError as exc:
        return {"error": str(exc)}

    url = (
        f"{get_region_host(region)}"
        f"/lol/challenges/v1/player-data/{encoded}"
    )

    return await riot_api_request(url)


async def get_challenge_config(
    challenge_id: int,
    region: str,
) -> Any:

    url = (
        f"{get_region_host(region)}"
        f"/lol/challenges/v1/challenges/{int(challenge_id)}"
    )

    return await riot_api_request(url)


# ---------------------------------------------------------------------------
# CLASH
# ---------------------------------------------------------------------------

async def get_clash_players(
    summoner_id: str,
    region: str,
) -> Any:

    try:
        encoded = _encode_path(summoner_id)
    except ValueError as exc:
        return {"error": str(exc)}

    url = (
        f"{get_region_host(region)}"
        f"/lol/clash/v1/players/by-summoner/{encoded}"
    )

    return await riot_api_request(url)


async def get_clash_teams(
    team_id: str,
    region: str,
) -> Any:

    try:
        encoded = _encode_path(team_id)
    except ValueError as exc:
        return {"error": str(exc)}

    url = (
        f"{get_region_host(region)}"
        f"/lol/clash/v1/teams/{encoded}"
    )

    return await riot_api_request(url)


async def get_clash_tournaments(
    region: str,
) -> Any:

    url = (
        f"{get_region_host(region)}"
        f"/lol/clash/v1/tournaments"
    )

    return await riot_api_request(url)


# ---------------------------------------------------------------------------
# STATUS
# ---------------------------------------------------------------------------

async def get_server_status(
    region: str,
) -> Any:

    url = (
        f"{get_region_host(region)}"
        f"/lol/status/v4/platform-data"
    )

    return await riot_api_request(url)


def is_error(value: Any) -> bool:
    return (
        isinstance(value, dict)
        and isinstance(value.get("error"), str)
    )