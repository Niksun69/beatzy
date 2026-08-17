import discord
from discord import app_commands
from utils.embed import error_embed, success_embed

class LeaveMixin:
    @app_commands.command(name="leave", description="Stop playback, disconnect, but keep the queue")
    async def leave(self, interaction: discord.Interaction):
        vc = interaction.guild.voice_client
        guild_id = interaction.guild.id

        if vc:
            # Cancel any pending idle timer
            if guild_id in self.idle_timer:
                self.idle_timer[guild_id].cancel()
                self.idle_timer.pop(guild_id, None)

            # Stop the update loop and clean pause state
            self._cancel_update_task(guild_id)
            self._cleanup_track_state(guild_id)

            # Stop playback and disconnect
            if vc.is_playing() or vc.is_paused():
                vc.stop()
            await vc.disconnect()

            # ✅ Disable 24/7 mode for this guild
            self.stay_connected.pop(guild_id, None)

            await interaction.response.send_message(
                embed=success_embed(
                    "👋 Disconnected",
                    "Disconnected from voice. Queue is preserved.\n24/7 mode has been **disabled**."
                )
            )
        else:
            await interaction.response.send_message(
                embed=error_embed("❌ Not Connected", "I'm not in a voice channel."),
                ephemeral=True
            )