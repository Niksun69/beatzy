import time
import discord
from discord import app_commands
from utils.embed import error_embed, info_embed

class PauseMixin:
    # ------------------------------------------------
    # Pause / Resume helpers (used by the view)
    # ------------------------------------------------
    def pause_track(self, guild_id):
        """
        Record the moment when the track was paused.
        """
        if guild_id not in self.pause_started:
            self.pause_started[guild_id] = time.time()

    def resume_track(self, guild_id):
        """
        When resuming, add the paused duration to the accumulated pause time
        and clear the pause-start marker.
        """
        if guild_id in self.pause_started:
            paused_duration = time.time() - self.pause_started.pop(guild_id)
            self.paused_time[guild_id] = self.paused_time.get(guild_id, 0) + paused_duration

    # ------------------------------------------------
    # Pause command
    # ------------------------------------------------
    @app_commands.command(name="pause", description="Pause playback")
    async def pause(self, interaction: discord.Interaction):
        vc = interaction.guild.voice_client

        if vc and vc.is_playing():
            self.pause_track(interaction.guild.id)
            vc.pause()
            await interaction.response.send_message(
                embed=info_embed("⏸️ Paused", "Playback has been paused.")
            )
        else:
            await interaction.response.send_message(
                embed=error_embed("❌ Cannot Pause", "I'm not currently playing anything."),
                ephemeral=True,
            )

    # ------------------------------------------------
    # Resume command (if you have one)
    # ------------------------------------------------
    @app_commands.command(name="resume", description="Resume playback")
    async def resume(self, interaction: discord.Interaction):
        vc = interaction.guild.voice_client
        if vc and vc.is_paused():
            self.resume_track(interaction.guild.id)
            vc.resume()
            await interaction.response.send_message(
                embed=info_embed("▶️ Resumed", "Playback has been resumed.")
            )
        else:
            await interaction.response.send_message(
                embed=error_embed("❌ Cannot Resume", "I'm not currently paused."),
                ephemeral=True,
            )