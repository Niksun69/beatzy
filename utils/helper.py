import asyncio
import time
import tempfile
import os
import yt_dlp
import discord
from utils.voice import get_current_track, get_queue, save_queue_to_db, set_current_track
from utils.embed import error_embed, now_playing_with_progress, MusicControlView, info_embed
from utils.yt import _build_ydl_options, extract_info
from config import YTDLP_COOKIES

class MusicHelpers:
    """Shared methods for the music cog.  The main cog will inherit from this."""

    # ========================================================
    # PLAY SONG
    # ========================================================
    
    async def _play_song(self, interaction, track):
        """
        Play a track by downloading the best audio file locally.
        """
        vc = interaction.guild.voice_client
        url = track.get("url")
    
        if not url:
            await interaction.followup.send(
                embed=error_embed("❌ Error", "No URL was provided."),
                ephemeral=True,
            )
            return
    
        # ----------------------------------------------------
        # Extract metadata (title, duration, thumbnail, artist)
        # ----------------------------------------------------
        info = extract_info(url, cookies=YTDLP_COOKIES)
        if not info or "url" not in info:
            await interaction.followup.send(
                embed=error_embed(
                    "❌ Extraction Failed",
                    "Could not extract audio from that URL. Skipping to next track.",
                ),
                ephemeral=True,
            )
            # Skip this track and move to the next
            await self._play_next(interaction)
            return
    
        title = info.get("title", "Unknown Track")
        duration = info.get("duration", 0) or 0
        thumbnail = info.get("thumbnail")
        artist = info.get("artist") or info.get("uploader") or info.get("channel")
        track["artist"] = artist
    
        # ----------------------------------------------------
        # Download the best audio (no extraction) to a temp file
        # ----------------------------------------------------
        # Create a temporary file without extension – yt-dlp will add the appropriate one.
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix="")
        temp_path = temp_file.name
        temp_file.close()
    
        # yt-dlp options: download best audio, save with the same base name + extension
        ydl_opts = _build_ydl_options(cookies=YTDLP_COOKIES)
        ydl_opts.update({
            "skip_download": False,
            "outtmpl": temp_path + ".%(ext)s",
        })
            
        def download_sync():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info_dl = ydl.extract_info(url, download=True)
                return ydl.prepare_filename(info_dl)

        try:
            # Run download in a separate thread, with a 60‑second timeout
            source_path = await asyncio.wait_for(
                asyncio.to_thread(download_sync),
                timeout=60.0
            )
        except asyncio.TimeoutError:
            await interaction.followup.send(
                embed=error_embed("❌ Download Timeout", "Download took too long."),
                ephemeral=True,
            )
            # Clean up any partial file?
            return
        except Exception as e:
            print(f"[Download] Failed: {e}")
            await interaction.followup.send(
                embed=error_embed("❌ Download Failed", "Could not download the audio track."),
                ephemeral=True,
            )
            return
    
        # ----------------------------------------------------
        # FFmpeg source (from local file)
        # ----------------------------------------------------
        # No reconnect needed; we'll use PCM with high bitrate.
        FFMPEG_OPTIONS = "-vn -b:a 192k -ar 48000 -ac 2 -bufsize 192k"
        source = discord.FFmpegPCMAudio(
            source_path,
            options=FFMPEG_OPTIONS,
        )
    
        # ----------------------------------------------------
        # Playback callback (clean up temp file and play next)
        # ----------------------------------------------------
        def after_play(error):
            try:
                os.remove(source_path)   # delete the downloaded file
                # Also remove any leftover .part files if any
                if os.path.exists(source_path + ".part"):
                    os.remove(source_path + ".part")
            except Exception:
                pass
            asyncio.run_coroutine_threadsafe(
                self._play_next(interaction),
                self.bot.loop,
            )

        vc.play(
            source,
            after=after_play,
            bitrate=256,
        )

        # ----------------------------------------------------
        # RECORD THE START TIME FOR PROGRESS TRACKING
        # ----------------------------------------------------
        # Offset to compensate for FFmpeg / Discord startup latency
        STARTUP_OFFSET = 0.8   # seconds
        self.play_start_time[interaction.guild.id] = time.time() - STARTUP_OFFSET
    
        # ----------------------------------------------------
        # Store current track info
        # ----------------------------------------------------
        guild_id = interaction.guild.id

        # If loop is enabled, store this track as the one to loop
        if self.loop_enabled.get(guild_id, False):
            self.loop_track[guild_id] = track
    
        # Cancel any pending idle timer
        if guild_id in self.idle_timer:
            self.idle_timer[guild_id].cancel()
            self.idle_timer.pop(guild_id, None)

        set_current_track(
            guild_id,
            title,
            url,
            thumbnail,
            duration,
        )
    
        # Reset pause tracking
        self._cleanup_track_state(guild_id)
    
        # Cancel previous update task
        self._cancel_update_task(guild_id)
    
        # ----------------------------------------------------
        # Queue count and embed
        # ----------------------------------------------------
        queue = get_queue(guild_id)
        view = MusicControlView(self, guild_id)
    
        embed = now_playing_with_progress(
            title=title,
            url=url,
            thumbnail=thumbnail,
            elapsed=0,
            duration=duration,
            queue_count=len(queue),
            paused=False,
        )
    
        # Reuse or create the Now Playing message
        old_message = self.current_messages.get(guild_id)
        old_view = self.current_views.get(guild_id)  
        msg = None
        if old_message:
            try:
                # Use the existing view if available; otherwise use the new one
                if old_view:
                    await old_message.edit(embed=embed, view=old_view)
                    msg = old_message
                    # keep the existing view (we don't replace it)
                else:
                    await old_message.edit(embed=embed, view=view)
                    msg = old_message
                    self.current_views[guild_id] = view
            except (discord.NotFound, discord.HTTPException):
                # message vanished – send a new one
                msg = await interaction.followup.send(embed=embed, view=view)
                self.current_views[guild_id] = view
        else:
            msg = await interaction.followup.send(embed=embed, view=view)
            self.current_views[guild_id] = view

        if msg:
            self.current_messages[guild_id] = msg
    
        # Start live updater
        task = asyncio.create_task(
            self._update_now_playing_loop(interaction, guild_id)
        )
        self.update_tasks[guild_id] = task

    # ========================================================
    # GO IDLE
    # ========================================================

    async def _go_idle(self, interaction):
        guild_id = interaction.guild.id
        save_queue_to_db(guild_id)

        message = self.current_messages.get(guild_id)
        if message:
            try:
                embed = info_embed(
                    "🎵 Music Player",
                    (
                        "Playback has finished.\n\n"
                        "The queue is empty. Use `/play` "
                        "to play something."
                    ),
                )
                if self.stay_connected.get(guild_id, False):
                    embed.description += "\n\n🔁 **24/7 mode is enabled** – I'll stay connected."
                await message.edit(embed=embed, view=None)
            except (discord.NotFound, discord.HTTPException):
                pass

        self.current_messages.pop(guild_id, None)

        if guild_id in self.idle_timer:
            self.idle_timer[guild_id].cancel()
            self.idle_timer.pop(guild_id, None)

        if not self.stay_connected.get(guild_id, False):
            self.idle_timer[guild_id] = asyncio.create_task(self._idle_timeout(guild_id))
        else:
            print(f"[247] Guild {guild_id} is idle but staying connected.")

    # ========================================================
    # PLAY NEXT
    # ========================================================
    
    async def _play_next(self, interaction):
        guild_id = interaction.guild.id

        # Stop updating the old track.
        self._cancel_update_task(guild_id)

        # Reset pause timing.
        self._cleanup_track_state(guild_id)

        # ------------------------------------------------------------------
        # Skip handling – if skip was triggered, advance to next track
        # ------------------------------------------------------------------
        if self.skip_triggered.pop(guild_id, False):
            queue = get_queue(guild_id)
            if queue:
                next_track = queue.pop(0)
                save_queue_to_db(guild_id)
                # If loop is on, update loop_track to the new track
                if self.loop_enabled.get(guild_id, False):
                    self.loop_track[guild_id] = next_track
                await self._play_song(interaction, next_track)
            else:
                # No queue – go to idle
                await self._go_idle(interaction)
            return

        # ------------------------------------------------------------------
        # Loop – if enabled and we have a loop track, repeat it
        # ------------------------------------------------------------------
        if self.loop_enabled.get(guild_id, False) and self.loop_track.get(guild_id):
            await self._play_song(interaction, self.loop_track[guild_id])
            return

        # ------------------------------------------------------------------
        # Normal queue pop
        # ------------------------------------------------------------------
        queue = get_queue(guild_id)
        if queue:
            next_track = queue.pop(0)
            save_queue_to_db(guild_id)
            # If loop is on, store this as the loop track for future repeats
            if self.loop_enabled.get(guild_id, False):
                self.loop_track[guild_id] = next_track
            await self._play_song(interaction, next_track)
        else:
            # Queue empty – go idle
            await self._go_idle(interaction)

    # ========================================================
    # IDLE TIMEOUT
    # ========================================================
    
    async def _idle_timeout(self, guild_id):
        await asyncio.sleep(60)   # 60 seconds of inactivity
        # Double-check that the bot is still idle (no voice client, or not playing)
        vc = self.bot.get_guild(guild_id).voice_client
        if vc and not vc.is_playing() and not vc.is_paused():
            # Ensure queue is still empty
            if not get_queue(guild_id):
                await vc.disconnect()

                self.current_messages.pop(guild_id, None)
                self.current_views.pop(guild_id, None)
                print(f"[Auto] Disconnected from guild {guild_id} after idle.")
        # Clean up the timer reference
        self.idle_timer.pop(guild_id, None)

    # ========================================================
    # TRACK STATE CLEANUP
    # ========================================================
    def _cleanup_track_state(self, guild_id):
        """
        Reset pause tracking for a guild.
        """
        self.paused_time.pop(guild_id, None)
        self.pause_started.pop(guild_id, None)

    # ========================================================
    # CANCEL UPDATE TASK
    # ========================================================
    def _cancel_update_task(self, guild_id):
        """
        Cancel the live progress‑update task for a guild, if any.
        """
        task = self.update_tasks.pop(guild_id, None)
        if task and not task.done():
            task.cancel()

    # ========================================================
    # NOW PLAYING UPDATE LOOP
    # ========================================================
    async def _update_now_playing_loop(self, interaction, guild_id):
        """
        Background loop that updates the Now Playing embed with elapsed time every 2 seconds.
        """
        await asyncio.sleep(1)  # wait for playback to start

        while True:
            try:
                # Use bot.get_guild to avoid stale interaction
                guild = self.bot.get_guild(guild_id)
                if not guild:
                    break
                vc = guild.voice_client
                if not vc:
                    break

                # Check if the task was cancelled
                if guild_id not in self.update_tasks:
                    break

                # Get current track info
                track = get_current_track(guild_id)
                if not track:
                    # No track yet, wait and retry
                    await asyncio.sleep(2)
                    continue

                # Calculate elapsed time
                elapsed = self._get_elapsed(guild_id)

                # Build updated embed
                queue = get_queue(guild_id)
                embed = now_playing_with_progress(
                    title=track.get('title', 'Unknown'),
                    url=track.get('url', ''),
                    thumbnail=track.get('thumbnail'),
                    elapsed=elapsed,
                    duration=track.get('duration', 0),
                    queue_count=len(queue),
                    paused=vc.is_paused() if vc else False,
                )

                # Edit the stored message
                msg = self.current_messages.get(guild_id)
                view = self.current_views.get(guild_id)
                if msg:
                    try:
                        if view:
                            await msg.edit(embed=embed, view=view)
                        else:
                            # fallback – create a new view
                            new_view = MusicControlView(self, guild_id)
                            await msg.edit(embed=embed, view=new_view)
                            self.current_views[guild_id] = new_view
                    except (discord.NotFound, discord.HTTPException):
                        # Message deleted – stop updating
                        break

            except Exception as e:
                print(f"[Update Loop] Error in guild {guild_id}: {e}")
                # Don't break, keep trying

            await asyncio.sleep(2)  # update every 2 seconds

        # Clean up when loop exits
        self.update_tasks.pop(guild_id, None)
        print(f"[Update Loop] Stopped for guild {guild_id}")

    # ========================================================
    # GET ELAPSED TIME (including pauses)
    # ========================================================
    def _get_elapsed(self, guild_id):
        vc = self.bot.get_guild(guild_id).voice_client
        if not vc:
            return 0

        start = self.play_start_time.get(guild_id)
        if not start:
            return 0

        # total paused time accumulated
        paused_accumulated = self.paused_time.get(guild_id, 0)

        # If currently paused, add the current pause duration
        if vc.is_paused():
            pause_start = self.pause_started.get(guild_id)
            if pause_start:
                paused_accumulated += time.time() - pause_start

        elapsed = time.time() - start - paused_accumulated
        return max(0, elapsed)