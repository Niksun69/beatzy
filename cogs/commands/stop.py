import discord
from discord import app_commands
from utils.embed import error_embed, success_embed

class StopMixin:
    @app_commands.command(name="stop", description="Stop playback and clear queue")
    async def stop(self, interaction: discord.Interaction):
        vc = interaction.guild.voice_client
        if vc and (vc.is_playing() or vc.is_paused()):
            self._cancel_update_task(interaction.guild.id)
            self._cleanup_track_state(interaction.guild.id)
            vc.stop()
            
            await interaction.response.send_message(
                embed=success_embed(
                    "⏹️ Stopped",
                    "Playback stopped. The queue remains intact."
                )
            )
        else:
            await interaction.response.send_message(
                embed=error_embed("❌ Nothing to Stop", "I'm not currently playing anything."),
                ephemeral=True
            )
    