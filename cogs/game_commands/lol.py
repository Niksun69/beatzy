import asyncio
from datetime import datetime, timezone

import discord
from discord import app_commands

from config import DEFAULT_REGION
from utils.embed import error_embed

from utils.riot import (
    get_active_game,
    get_all_champion_masteries_by_puuid,
    get_challenges,
    get_champion_map,
    get_clash_players,
    get_clash_teams,
    get_match_details,
    get_match_ids_by_puuid,
    get_ranked_entries_by_puuid,
    get_static_data,
    get_summoner_data,
    is_error,
)


ALLOWED_REGIONS = [
    "br1",
    "eun1",
    "euw1",
    "jp1",
    "kr",
    "la1",
    "la2",
    "na1",
    "oc1",
    "tr1",
    "ru",
    "me1",
    "ph2",
    "sg2",
    "tw2",
    "vn2",
]


QUEUE_NAMES = {
    0: "Custom",
    2: "5v5 Blind",
    4: "Ranked Solo",
    6: "Ranked Premade",
    7: "Co-op vs AI",
    8: "3v3 Normal",
    14: "5v5 Draft",
    16: "Dominion",
    17: "Dominion Coop",
    25: "Dominion",
    30: "5v5 Ranked",
    31: "Co-op vs AI",
    32: "Co-op vs AI",
    33: "Co-op vs AI",
    52: "3v3 Coop",
    61: "5v5 Team Builder",
    65: "ARAM",
    67: "ARAM",
    70: "One for All",
    72: "1v1 Snowdown",
    73: "2v2 Snowdown",
    75: "6v6 Hexakill",
    76: "URF",
    78: "One for All",
    83: "Co-op vs AI",
    98: "6v6 Hexakill",
    100: "ARAM",
    102: "6v6",
    130: "Nexus Blitz",
    300: "ARAM",
    310: "Nemesis",
    313: "Black Market",
    315: "Nexus Siege",
    317: "Definitely Not Dominion",
    318: "ARURF",
    325: "Nexus Blitz",
    400: "Normal Draft",
    410: "Ranked Dynamic",
    420: "Ranked Solo/Duo",
    430: "Normal Blind",
    440: "Ranked Flex",
    450: "ARAM",
    490: "Quickplay",
    600: "Blood Hunt",
    610: "Teamfight Tactics",
    700: "Clash",
    800: "Co-op vs AI",
    810: "Co-op vs AI",
    820: "Co-op vs AI",
    830: "Co-op vs AI",
    840: "Co-op vs AI",
    850: "Co-op vs AI",
    900: "ARURF",
    1020: "One for All",
    1300: "Nexus Blitz",
    1400: "Ultimate Spellbook",
    1700: "Arena",
    1710: "Arena",
    1810: "Swarm",
    1820: "Swarm",
    1830: "Swarm",
    1840: "Swarm",
    1850: "Swarm",
    1860: "Swarm",
    1870: "Swarm",
    1880: "Swarm",
    1890: "Swarm",
    1900: "Pick URF",
}


def compact_number(value) -> str:
    try:
        value = int(value)
    except (TypeError, ValueError):
        return "0"

    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"

    if value >= 1_000:
        return f"{value / 1_000:.1f}k"

    return f"{value:,}"


def truncate(text: str, limit: int = 1024) -> str:
    text = str(text)

    if len(text) <= limit:
        return text

    return text[: limit - 1] + "…"


def duration_text(seconds) -> str:
    try:
        seconds = int(seconds)
    except (TypeError, ValueError):
        return "?"

    return f"{seconds // 60}:{seconds % 60:02d}"


def rank_text(entry) -> str:
    if not entry:
        return "Unranked"

    tier = str(
        entry.get("tier", "UNRANKED")
    ).title()

    rank = entry.get("rank", "")
    lp = entry.get("leaguePoints", 0)

    wins = int(entry.get("wins", 0) or 0)
    losses = int(entry.get("losses", 0) or 0)

    games = wins + losses
    win_rate = (
        wins / games * 100
        if games
        else 0
    )

    flags = []

    if entry.get("hotStreak"):
        flags.append("🔥 Hot streak")

    if entry.get("veteran"):
        flags.append("Veteran")

    if entry.get("freshBlood"):
        flags.append("Fresh blood")

    if entry.get("inactive"):
        flags.append("Inactive")

    flags_text = (
        "\n" + " • ".join(flags)
        if flags
        else ""
    )

    return (
        f"**{tier} {rank}** • **{lp} LP**\n"
        f"⚔️ {wins}W - {losses}L • "
        f"**{win_rate:.1f}% WR**"
        f"{flags_text}"
    )


def get_rank_color(entry):
    colors = {
        "CHALLENGER": 0x00D4FF,
        "GRANDMASTER": 0xE74C3C,
        "MASTER": 0x9B59B6,
        "DIAMOND": 0x3498DB,
        "EMERALD": 0x2ECC71,
        "PLATINUM": 0x1ABC9C,
        "GOLD": 0xF1C40F,
        "SILVER": 0x95A5A6,
        "BRONZE": 0xCD7F32,
        "IRON": 0x555555,
    }

    tier = str(
        (entry or {}).get("tier", "")
    ).upper()

    return discord.Color(
        colors.get(
            tier,
            0x5865F2,
        )
    )


def participant_for_puuid(match, puuid):
    participants = (
        match.get("info", {})
        .get("participants", [])
    )

    return next(
        (
            p
            for p in participants
            if p.get("puuid") == puuid
        ),
        None,
    )


def get_item_names(player, item_map):
    names = []

    for slot in range(7):
        item_id = player.get(
            f"item{slot}",
            0,
        )

        if not item_id:
            continue

        item = item_map.get(
            int(item_id),
            {},
        )

        names.append(
            item.get(
                "name",
                f"Item {item_id}",
            )
        )

    return names


def match_line(
    match,
    player,
    champion_map,
    queue_map,
):
    info = match.get("info", {})
    metadata = match.get("metadata", {})

    champion_id = player.get(
        "championId"
    )

    champion = champion_map.get(
        champion_id,
        {},
    ).get(
        "name",
        player.get(
            "championName",
            f"Champion {champion_id}",
        ),
    )

    result = (
        "🟢 WIN"
        if player.get("win")
        else "🔴 LOSS"
    )

    queue_id = info.get(
        "queueId",
        0,
    )

    queue_name = (
        queue_map.get(queue_id)
        or QUEUE_NAMES.get(queue_id)
        or info.get(
            "gameMode",
            "Unknown",
        )
    )

    kills = int(
        player.get("kills", 0)
        or 0
    )

    deaths = int(
        player.get("deaths", 0)
        or 0
    )

    assists = int(
        player.get("assists", 0)
        or 0
    )

    kda = (
        kills + assists
    ) / max(
        deaths,
        1,
    )

    cs = (
        int(player.get("totalMinionsKilled", 0) or 0)
        + int(player.get("neutralMinionsKilled", 0) or 0)
    )

    match_id = metadata.get(
        "matchId",
        "Unknown",
    )

    return (
        f"{result} **{champion}** • "
        f"`{kills}/{deaths}/{assists}` • "
        f"**{kda:.2f} KDA**\n"
        f"└ {queue_name} • "
        f"{duration_text(info.get('gameDuration'))} • "
        f"{cs} CS • `{match_id}`"
    )


class LolMixin:

    @app_commands.command(
        name="lol",
        description=(
            "Show a detailed League of Legends "
            "profile by Riot ID."
        ),
    )
    @app_commands.describe(
        summoner=(
            "Riot ID, e.g. Faker#KR1"
        ),
        region=(
            "League platform, e.g. euw1, na1, kr"
        ),
    )
    async def lol_command(
        self,
        interaction: discord.Interaction,
        summoner: str,
        region: str = DEFAULT_REGION,
    ):

        await interaction.response.defer(
            thinking=True
        )

        region = (
            region or ""
        ).lower().strip()

        if region not in ALLOWED_REGIONS:
            await interaction.followup.send(
                embed=error_embed(
                    "❌ Invalid region",
                    (
                        "Use one of: "
                        + ", ".join(
                            ALLOWED_REGIONS
                        )
                    ),
                ),
                ephemeral=True,
            )
            return

        summoner = (
            summoner or ""
        ).strip()

        if summoner.count("#") != 1:
            await interaction.followup.send(
                embed=error_embed(
                    "❌ Invalid Riot ID",
                    (
                        "Use `gameName#tagLine`, "
                        "for example `bochko1#1233`."
                    ),
                ),
                ephemeral=True,
            )
            return

        game_name, tag_line = (
            x.strip()
            for x in summoner.split(
                "#",
                1,
            )
        )

        if not game_name or not tag_line:
            await interaction.followup.send(
                embed=error_embed(
                    "❌ Invalid Riot ID",
                    "Both game name and tag line are required.",
                ),
                ephemeral=True,
            )
            return

        # ---------------------------------------------------------------
        # ACCOUNT
        # ---------------------------------------------------------------

        profile = await get_summoner_data(
            f"{game_name}#{tag_line}",
            region,
        )

        if not profile or is_error(profile):
            message = (
                profile.get(
                    "error",
                    "Player not found.",
                )
                if isinstance(profile, dict)
                else "Player not found."
            )

            await interaction.followup.send(
                embed=error_embed(
                    "❌ Could not fetch player",
                    message,
                ),
                ephemeral=True,
            )
            return

        # PUUID is mandatory.
        puuid = profile.get(
            "_puuid"
        )

        if not puuid:
            await interaction.followup.send(
                embed=error_embed(
                    "❌ Riot response incomplete",
                    (
                        "The Riot account was found, but "
                        "Riot did not return a PUUID. "
                        "Try again in a moment."
                    ),
                ),
                ephemeral=True,
            )
            return

        # The summoner ID is intentionally optional.
        # Some Riot responses no longer provide it.
        summoner_id = profile.get("id")

        # ---------------------------------------------------------------
        # FETCH EVERYTHING POSSIBLE THAT WE CAN FETCH WITHOUT DEPENDING
        # ON THE OPTIONAL SUMMONER ID.
        # ---------------------------------------------------------------

        ranked_task = get_ranked_entries_by_puuid(
            puuid,
            region,
        )

        mastery_task = get_all_champion_masteries_by_puuid(
            puuid,
            region,
        )

        matches_task = get_match_ids_by_puuid(
            puuid,
            region,
            count=20,
        )

        live_task = get_active_game(
            puuid,
            region,
        )

        challenges_task = get_challenges(
            puuid,
            region,
        )

        static_task = get_static_data()

        # Clash still requires the old summoner ID.
        # Only request it when Riot actually returned one.
        if summoner_id:
            clash_task = get_clash_players(
                summoner_id,
                region,
            )
        else:
            clash_task = asyncio.sleep(
                0,
                result=None,
            )

        (
            ranked,
            masteries,
            match_ids,
            live_game,
            challenges,
            static,
            clash_players,
        ) = await asyncio.gather(
            ranked_task,
            mastery_task,
            matches_task,
            live_task,
            challenges_task,
            static_task,
            clash_task,
        )

        warnings = []

        results = {
            "Ranked": ranked,
            "Mastery": masteries,
            "Matches": match_ids,
            "Live": live_game,
            "Challenges": challenges,
        }

        if summoner_id:
            results["Clash"] = clash_players
        else:
            warnings.append(
                "Clash unavailable because Riot did not return a Summoner ID."
            )

        for label, result in results.items():
            if is_error(result):
                warnings.append(
                    f"{label}: {result.get('error')}"
                )

        ranked = (
            []
            if is_error(ranked)
            or not isinstance(ranked, list)
            else ranked
        )

        masteries = (
            []
            if is_error(masteries)
            or not isinstance(masteries, list)
            else masteries
        )

        match_ids = (
            []
            if is_error(match_ids)
            or not isinstance(match_ids, list)
            else match_ids
        )

        live_game = (
            None
            if is_error(live_game)
            else live_game
        )

        challenges = (
            {}
            if is_error(challenges)
            or not isinstance(
                challenges,
                dict,
            )
            else challenges
        )

        clash_players = (
            []
            if is_error(clash_players)
            or not isinstance(
                clash_players,
                list,
            )
            else clash_players
        )

        # ---------------------------------------------------------------
        # STATIC DATA
        # ---------------------------------------------------------------

        champion_map = static.get(
            "champions",
            {},
        )

        item_map = static.get(
            "items",
            {},
        )

        queue_map = static.get(
            "queues",
            {},
        )

        # ---------------------------------------------------------------
        # MATCH DETAILS
        # ---------------------------------------------------------------

        match_details = []

        if match_ids:
            raw_matches = await asyncio.gather(
                *(
                    get_match_details(
                        match_id,
                        region,
                    )
                    for match_id in match_ids[:20]
                ),
                return_exceptions=True,
            )

            for match in raw_matches:

                if (
                    isinstance(match, dict)
                    and "info" in match
                ):
                    match_details.append(match)

                elif (
                    isinstance(match, dict)
                    and "error" in match
                ):
                    warnings.append(
                        f"Match: {match['error']}"
                    )

        # ---------------------------------------------------------------
        # RANKED
        # ---------------------------------------------------------------

        solo = next(
            (
                entry
                for entry in ranked
                if entry.get(
                    "queueType"
                ) == "RANKED_SOLO_5x5"
            ),
            None,
        )

        flex = next(
            (
                entry
                for entry in ranked
                if entry.get(
                    "queueType"
                ) == "RANKED_FLEX_SR"
            ),
            None,
        )

        # ---------------------------------------------------------------
        # RECENT MATCH STATISTICS
        # ---------------------------------------------------------------

        wins = 0
        losses = 0

        kills = 0
        deaths = 0
        assists = 0
        cs_total = 0

        champion_games = {}
        recent_lines = []

        for match in match_details:

            player = participant_for_puuid(
                match,
                puuid,
            )

            if not player:
                continue

            if player.get("win"):
                wins += 1
            else:
                losses += 1

            kills += int(
                player.get(
                    "kills",
                    0,
                )
                or 0
            )

            deaths += int(
                player.get(
                    "deaths",
                    0,
                )
                or 0
            )

            assists += int(
                player.get(
                    "assists",
                    0,
                )
                or 0
            )

            cs_total += (
                int(
                    player.get(
                        "totalMinionsKilled",
                        0,
                    )
                    or 0
                )
                + int(
                    player.get(
                        "neutralMinionsKilled",
                        0,
                    )
                    or 0
                )
            )

            champion_id = player.get(
                "championId"
            )

            champion_name = champion_map.get(
                champion_id,
                {},
            ).get(
                "name",
                player.get(
                    "championName",
                    f"Champion {champion_id}",
                ),
            )

            champion_games[
                champion_name
            ] = (
                champion_games.get(
                    champion_name,
                    0,
                )
                + 1
            )

            if len(recent_lines) < 8:
                recent_lines.append(
                    match_line(
                        match,
                        player,
                        champion_map,
                        queue_map,
                    )
                )

        recent_games = (
            wins + losses
        )

        recent_win_rate = (
            wins / recent_games * 100
            if recent_games
            else 0
        )

        avg_kda = (
            kills + assists
        ) / max(
            deaths,
            1,
        )

        avg_cs = (
            cs_total / recent_games
            if recent_games
            else 0
        )

        # ---------------------------------------------------------------
        # MASTERY
        # ---------------------------------------------------------------

        total_mastery = sum(
            int(
                mastery.get(
                    "championPoints",
                    0,
                )
                or 0
            )
            for mastery in masteries
        )

        level7 = sum(
            1
            for mastery in masteries
            if mastery.get(
                "championLevel"
            ) == 7
        )

        level6 = sum(
            1
            for mastery in masteries
            if mastery.get(
                "championLevel"
            ) == 6
        )

        level5 = sum(
            1
            for mastery in masteries
            if mastery.get(
                "championLevel"
            ) == 5
        )

        top_masteries = sorted(
            masteries,
            key=lambda mastery: int(
                mastery.get(
                    "championPoints",
                    0,
                )
                or 0
            ),
            reverse=True,
        )[:8]

        mastery_lines = []

        for mastery in top_masteries:

            champion_id = mastery.get(
                "championId"
            )

            champion_name = champion_map.get(
                champion_id,
                {},
            ).get(
                "name",
                f"Champion {champion_id}",
            )

            mastery_lines.append(
                f"**{champion_name}** • "
                f"M{mastery.get('championLevel', 0)} • "
                f"{compact_number(mastery.get('championPoints', 0))} pts"
            )

        # ---------------------------------------------------------------
        # CHALLENGES
        # ---------------------------------------------------------------

        total_points = challenges.get(
            "totalPoints",
            {},
        )

        if isinstance(
            total_points,
            dict,
        ):
            challenge_points = (
                total_points.get(
                    "current",
                    total_points.get(
                        "points",
                        0,
                    ),
                )
            )
        else:
            challenge_points = (
                total_points or 0
            )

        challenge_list = challenges.get(
            "challenges",
            [],
        )

        completed_challenges = [
            challenge
            for challenge in challenge_list
            if (
                isinstance(
                    challenge,
                    dict,
                )
                and challenge.get(
                    "completed"
                )
            )
        ]

        completed_challenges.sort(
            key=lambda challenge: challenge.get(
                "value",
                0,
            ),
            reverse=True,
        )

        challenge_lines = [
            (
                f"**{challenge.get('name', 'Challenge')}** • "
                f"{challenge.get('value', 0):,}"
            )
            for challenge in completed_challenges[:6]
        ]

        # ---------------------------------------------------------------
        # LIVE GAME
        # ---------------------------------------------------------------

        live_text = (
            "⚪ Not currently in a game."
        )

        live_extra = None

        if (
            isinstance(
                live_game,
                dict,
            )
            and live_game.get(
                "gameId"
            )
        ):

            participants = live_game.get(
                "participants",
                [],
            )

            me = next(
                (
                    participant
                    for participant in participants
                    if participant.get(
                        "puuid"
                    ) == puuid
                ),
                None,
            )

            if me:

                champion_name = champion_map.get(
                    me.get(
                        "championId"
                    ),
                    {},
                ).get(
                    "name",
                    me.get(
                        "championId",
                        "Unknown",
                    ),
                )

                my_team = me.get(
                    "teamId"
                )

                allies = [
                    champion_map.get(
                        participant.get(
                            "championId"
                        ),
                        {},
                    ).get(
                        "name",
                        str(
                            participant.get(
                                "championId"
                            )
                        ),
                    )
                    for participant in participants
                    if (
                        participant.get(
                            "teamId"
                        )
                        == my_team
                        and participant.get(
                            "puuid"
                        )
                        != puuid
                    )
                ]

                enemies = [
                    champion_map.get(
                        participant.get(
                            "championId"
                        ),
                        {},
                    ).get(
                        "name",
                        str(
                            participant.get(
                                "championId"
                            )
                        ),
                    )
                    for participant in participants
                    if participant.get(
                        "teamId"
                    ) != my_team
                ]

                live_text = (
                    f"🟢 **IN GAME** • "
                    f"**{champion_name}**\n"
                    f"Mode: `{live_game.get('gameMode', 'Unknown')}`\n"
                    f"Queue ID: `{live_game.get('gameQueueConfigId', '?')}`"
                )

                live_extra = (
                    f"**Allies:** "
                    f"{', '.join(allies) or 'N/A'}\n"
                    f"**Enemies:** "
                    f"{', '.join(enemies) or 'N/A'}"
                )

        # ---------------------------------------------------------------
        # CLASH
        # ---------------------------------------------------------------

        clash_text = (
            "No active Clash team."
        )

        if clash_players:

            team_ids = {
                player.get(
                    "teamId"
                )
                for player in clash_players
                if player.get(
                    "teamId"
                )
            }

            if team_ids:

                team_id = next(
                    iter(team_ids)
                )

                team = await get_clash_teams(
                    team_id,
                    region,
                )

                if (
                    isinstance(
                        team,
                        dict,
                    )
                    and not is_error(team)
                ):
                    clash_text = (
                        f"🏟️ **{team.get('name', 'Unnamed team')}**\n"
                        f"Tier: {team.get('tier', 'N/A')} • "
                        f"Tournament: "
                        f"`{team.get('tournamentId', 'N/A')}`"
                    )

        # ---------------------------------------------------------------
        # PROFILE
        # ---------------------------------------------------------------

        profile_icon_id = profile.get(
            "profileIconId",
            0,
        )

        ddragon_version = static.get(
            "version",
            "16.9.1",
        )

        icon_url = (
            f"https://ddragon.leagueoflegends.com/cdn/"
            f"{ddragon_version}/img/profileicon/"
            f"{profile_icon_id}.png"
        )

        revision_date = profile.get(
            "revisionDate"
        )

        if revision_date:

            try:
                last_modified = datetime.fromtimestamp(
                    int(revision_date) / 1000,
                    tz=timezone.utc,
                ).strftime(
                    "%Y-%m-%d %H:%M UTC"
                )
            except (
                TypeError,
                ValueError,
                OverflowError,
            ):
                last_modified = "Unknown"

        else:
            last_modified = "Unknown"

        # ---------------------------------------------------------------
        # EMBED
        # ---------------------------------------------------------------

        embed_color = get_rank_color(
            solo or flex
        )

        riot_id = (
            f"{game_name}#{tag_line}"
        )

        embed = discord.Embed(
            title=f"🏆 {riot_id}",
            description=(
                f"**Level {profile.get('summonerLevel', 0)}** • "
                f"`{region.upper()}`\n"
                f"PUUID: `{str(puuid)[:20]}…`"
            ),
            color=embed_color,
            timestamp=datetime.now(
                timezone.utc
            ),
        )

        embed.set_thumbnail(
            url=icon_url
        )

        # Ranked.
        embed.add_field(
            name="⚔️ Ranked Solo/Duo",
            value=rank_text(solo),
            inline=True,
        )

        embed.add_field(
            name="⚔️ Ranked Flex",
            value=rank_text(flex),
            inline=True,
        )

        embed.add_field(
            name="📈 Recent 20",
            value=(
                f"**{recent_win_rate:.1f}% WR**\n"
                f"{wins}W / {losses}L\n"
                f"**{avg_kda:.2f} KDA**\n"
                f"**{avg_cs:.1f} CS/game**"
            ),
            inline=True,
        )

        # Account.
        account_text = (
            f"Riot ID: `{riot_id}`\n"
            f"Level: **{profile.get('summonerLevel', 0)}**\n"
            f"Last modified: `{last_modified}`"
        )

        if summoner_id:
            account_text += (
                f"\nSummoner ID: `{str(summoner_id)[:20]}…`"
            )

        embed.add_field(
            name="👤 Account",
            value=account_text,
            inline=False,
        )

        # Mastery.
        mastery_text = (
            f"**{len(masteries)}** champions • "
            f"**{total_mastery:,}** total points\n"
            f"M7: **{level7}** • "
            f"M6: **{level6}** • "
            f"M5: **{level5}**\n\n"
        )

        mastery_text += (
            "\n".join(
                mastery_lines
            )
            if mastery_lines
            else "No mastery data."
        )

        embed.add_field(
            name="🏅 Champion Mastery",
            value=truncate(
                mastery_text
            ),
            inline=False,
        )

        # Recent matches.
        embed.add_field(
            name="🎮 Recent Matches",
            value=truncate(
                "\n\n".join(
                    recent_lines
                )
                if recent_lines
                else "No recent matches."
            ),
            inline=False,
        )

        # Champion pool.
        if champion_games:

            popular_champions = sorted(
                champion_games.items(),
                key=lambda item: item[1],
                reverse=True,
            )[:8]

            embed.add_field(
                name="🧙 Recent Champion Pool",
                value="\n".join(
                    (
                        f"**{champion}** — "
                        f"{games} game(s)"
                    )
                    for champion, games
                    in popular_champions
                ),
                inline=True,
            )

        # Challenges.
        challenge_text = (
            f"**{int(challenge_points or 0):,} points**\n"
        )

        challenge_text += (
            "\n".join(
                challenge_lines
            )
            if challenge_lines
            else "No completed challenge data."
        )

        embed.add_field(
            name="🏅 Challenges",
            value=truncate(
                challenge_text
            ),
            inline=True,
        )

        # Live.
        live_value = live_text

        if live_extra:
            live_value += (
                "\n\n"
                + live_extra
            )

        embed.add_field(
            name="🎯 Live Game",
            value=truncate(
                live_value
            ),
            inline=False,
        )

        # Clash.
        embed.add_field(
            name="🏟️ Clash",
            value=clash_text,
            inline=True,
        )

        # Warnings.
        if warnings:

            embed.add_field(
                name="⚠️ API Warnings",
                value=truncate(
                    "\n".join(
                        f"• {warning}"
                        for warning in warnings
                    )
                ),
                inline=False,
            )

        embed.set_footer(
            text=(
                "Riot Games API • "
                f"Data Dragon {ddragon_version}"
            )
        )

        # ---------------------------------------------------------------
        # SECOND EMBED — LAST GAME DETAIL
        # ---------------------------------------------------------------

        detail_embed = discord.Embed(
            title=(
                f"📊 {riot_id} — Last Game Details"
            ),
            color=embed_color,
        )

        if match_details:

            latest_player = participant_for_puuid(
                match_details[0],
                puuid,
            )

            if latest_player:

                latest_champion = champion_map.get(
                    latest_player.get(
                        "championId"
                    ),
                    {},
                ).get(
                    "name",
                    latest_player.get(
                        "championName",
                        "Unknown",
                    ),
                )

                items = get_item_names(
                    latest_player,
                    item_map,
                )

                latest_text = (
                    f"Champion: **{latest_champion}**\n"
                    f"KDA: "
                    f"`{latest_player.get('kills', 0)}/"
                    f"{latest_player.get('deaths', 0)}/"
                    f"{latest_player.get('assists', 0)}`\n"
                    f"CS: **{int(latest_player.get('totalMinionsKilled', 0) or 0) + int(latest_player.get('neutralMinionsKilled', 0) or 0)}**\n"
                    f"Damage: **{int(latest_player.get('totalDamageDealtToChampions', 0) or 0):,}**\n"
                    f"Gold: **{int(latest_player.get('goldEarned', 0) or 0):,}**\n"
                    f"Vision score: **{latest_player.get('visionScore', 0)}**\n"
                    f"Level: **{latest_player.get('champLevel', 0)}**\n"
                    f"Items: "
                    f"{', '.join(items) if items else 'None'}"
                )

                detail_embed.add_field(
                    name="🛡️ Build & Performance",
                    value=truncate(
                        latest_text
                    ),
                    inline=False,
                )

        # PUUID is the important persistent identifier.
        ids_text = (
            f"PUUID: `{puuid}`"
        )

        if summoner_id:
            ids_text += (
                f"\nSummoner ID: `{summoner_id}`"
            )

        detail_embed.add_field(
            name="🔑 Riot Identifiers",
            value=truncate(
                ids_text
            ),
            inline=False,
        )

        if warnings:

            detail_embed.add_field(
                name="⚠️ Warnings",
                value=truncate(
                    "\n".join(
                        f"• {warning}"
                        for warning in warnings
                    )
                ),
                inline=False,
            )

        detail_embed.set_footer(
            text=(
                "Riot Games API • "
                f"Data Dragon {ddragon_version}"
            )
        )

        await interaction.followup.send(
            embeds=[
                embed,
                detail_embed,
            ]
        )