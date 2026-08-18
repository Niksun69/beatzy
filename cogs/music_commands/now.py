import asyncio
import discord
from discord import app_commands
from utils.embed import MusicControlView, error_embed, now_playing_with_progress
from utils.voice import get_current_track, get_queue

class NowMixin:
    @app_commands.command(name="now", description="Show the currently playing track")
    async def now(self, interaction: discord.Interaction):
        vc = interaction.guild.voice_client

        if not vc or not (vc.is_playing() or vc.is_paused()):
            await interaction.response.send_message(
                embed=error_embed("❌ Nothing Playing", "I'm not playing anything right now."),
                ephemeral=True,
            )
            return

        track = get_current_track(interaction.guild.id)
        if not track:
            await interaction.response.send_message(
                embed=error_embed("❌ No Track Info", "I don't have information about the current track."),
                ephemeral=True,
            )
            return

        guild_id = interaction.guild.id

        # --- Delete old Now Playing message (if exists) ---
        old_msg = self.current_messages.pop(guild_id, None)
        if old_msg:
            try:
                await old_msg.delete()
            except (discord.NotFound, discord.HTTPException):
                pass   # already gone

        # --- Stop the previous update loop ---
        self._cancel_update_task(guild_id)

        # --- Build the embed ---
        elapsed = self._get_elapsed(guild_id)
        queue = get_queue(guild_id)
        embed = now_playing_with_progress(
            title=track.get("title", "Unknown Track"),
            url=track.get("url"),
            thumbnail=track.get("thumbnail"),
            elapsed=elapsed,
            duration=track.get("duration", 0),
            queue_count=len(queue),
            paused=vc.is_paused(),
        )

        # --- Create the view and sync its pause state ---
        view = MusicControlView(self, guild_id)
        view.paused = vc.is_paused()
        view._update_pause_button()

        # --- Send the new message (non‑ephemeral) and store it ---
        await interaction.response.send_message(embed=embed, view=view)
        msg = await interaction.original_response()
        self.current_messages[guild_id] = msg

        # --- Restart the update loop for this new message ---
        task = asyncio.create_task(
            self._update_now_playing_loop(interaction, guild_id)
        )
        self.update_tasks[guild_id] = task