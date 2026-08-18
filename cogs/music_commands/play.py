import discord
from discord import app_commands
from typing import Optional
from utils.embed import error_embed, info_embed, success_embed
from utils.spotify import get_spotify_track
from utils.voice import get_queue, save_queue_to_db
from utils.yt import extract_info, get_playlist_entries, is_valid_video_id
from config import YTDLP_COOKIES

class PlayMixin:
    @app_commands.command(name="play", description="Play a track, playlist, or resume the queue")
    async def play(
        self,
        interaction: discord.Interaction,
        query: Optional[str] = None,
    ):
        await interaction.response.defer()

        # ----------------------------------------------------
        # Voice check (user must be in a channel)
        # ----------------------------------------------------
        if not interaction.user.voice:
            await interaction.followup.send(
                embed=error_embed("❌ Not in Voice", "You must be in a voice channel."),
                ephemeral=True,
            )
            return

        guild_id = interaction.guild.id
        queue = get_queue(guild_id)
        vc = interaction.guild.voice_client

        # ====================================================
        # CONTINUE QUEUE (no query)
        # ====================================================
        if query is None:
            if not queue:
                await interaction.followup.send(
                    embed=error_embed("❌ Queue Empty", "There are no tracks in the queue."),
                    ephemeral=True,
                )
                return

            # Connect if not already connected
            if vc is None:
                channel = interaction.user.voice.channel
                await channel.connect()
                vc = interaction.guild.voice_client

            if vc.is_playing() or vc.is_paused():
                await interaction.followup.send(
                    embed=info_embed("ℹ️ Already Playing", "Music is already active."),
                    ephemeral=True,
                )
                return

            next_track = queue.pop(0)
            save_queue_to_db(guild_id)
            await self._play_song(interaction, next_track)
            return

        # ====================================================
        # PLAYLIST (if query contains list= or playlist)
        # ====================================================
        if "list=" in query or "playlist" in query.lower() or "/sets/" in query:
            entries = get_playlist_entries(query, cookies=YTDLP_COOKIES)
            if not entries:
                await interaction.followup.send(
                    embed=error_embed("❌ Playlist Error", "Could not extract any valid entries from that playlist."),
                    ephemeral=True,
                )
                return

            valid_entries = [e for e in entries if is_valid_video_id(e['id'])]
            if not valid_entries:
                await interaction.followup.send(
                    embed=error_embed("❌ Playlist Error", "No valid video IDs were found."),
                    ephemeral=True,
                )
                return

            # Multiple tracks
            if len(valid_entries) > 1:
                for entry in valid_entries:
                    vid = entry['id']
                    title = entry.get('title', 'Unknown Title')
                    duration = entry.get('duration')
                    url = f"https://www.youtube.com/watch?v={vid}"
                    queue.append({
                        "url": url,
                        "title": title,
                        "duration": duration,
                    })
                save_queue_to_db(guild_id)
                await interaction.followup.send(
                    embed=success_embed("✅ Playlist Added", f"Added **{len(valid_entries)}** tracks to the queue.")
                )

                # If nothing is playing, connect and start playing
                if not (vc and (vc.is_playing() or vc.is_paused())):
                    if vc is None:
                        channel = interaction.user.voice.channel
                        await channel.connect()
                        vc = interaction.guild.voice_client
                    next_track = queue.pop(0)
                    save_queue_to_db(guild_id)
                    await self._play_song(interaction, next_track)
                return

            # Single video inside playlist – treat as single track
            query = f"https://www.youtube.com/watch?v={valid_entries[0]['id']}"

        # ====================================================
        # SINGLE TRACK (URL or search)
        # ====================================================
        spotify_metadata = None

        if "open.spotify.com/track/" in query:
            spotify_metadata = get_spotify_track(query)
            if not spotify_metadata:
                await interaction.followup.send(
                    embed=error_embed("❌ Spotify Error", "Could not fetch track info."),
                    ephemeral=True,
                )
                return
            # Use the Spotify search query to find a YouTube video
            query = spotify_metadata["search_query"]

        # Extract YouTube video info (we need the actual audio URL)
        info = extract_info(query, cookies=YTDLP_COOKIES)
        if not info:
            await interaction.followup.send(
                embed=error_embed(
                    "❌ No Results",
                    f"Could not find a video for `{query}`.",
                ),
                ephemeral=True,
            )
            return

        # Build track dict – prefer Spotify metadata if available
        track = {
            "url": info.get("webpage_url") or query,               # always from YouTube
            "title": spotify_metadata.get("title") if spotify_metadata else info.get("title", "Unknown Track"),
            "duration": spotify_metadata.get("duration") if spotify_metadata else info.get("duration", 0),
            "artist": spotify_metadata.get("artist") if spotify_metadata else info.get("artist"),
            "thumbnail": info.get("thumbnail"),                    # you can also grab album art from Spotify
        }

        # If already playing, add to queue; otherwise play immediately
        if vc and (vc.is_playing() or vc.is_paused()):
            queue.append(track)
            save_queue_to_db(guild_id)
            await interaction.followup.send(
                embed=info_embed("📥 Added to Queue", f"**{track['title']}**")
            )
        else:
            if vc is None:
                channel = interaction.user.voice.channel
                await channel.connect()
                vc = interaction.guild.voice_client
            await self._play_song(interaction, track)