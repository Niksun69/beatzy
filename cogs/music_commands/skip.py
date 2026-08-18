import discord
from discord import app_commands
from utils.embed import error_embed, success_embed

class SkipMixin:
    @app_commands.command(name="skip", description="Skip the current track")
    async def skip(
        self,
        interaction: discord.Interaction,
    ):
        vc = interaction.guild.voice_client

        if vc and (
            vc.is_playing()
            or vc.is_paused()
        ):
            guild_id = interaction.guild.id

            self._cancel_update_task(guild_id)
            self._cleanup_track_state(guild_id)

            # This triggers _play_next(), which reuses
            # the existing Now Playing message.
            vc.stop()

            await interaction.response.send_message(
                embed=success_embed(
                    "⏭️ Skipped",
                    "Current track was skipped.",
                ),
                ephemeral=True,
            )

        else:
            await interaction.response.send_message(
                embed=error_embed(
                    "❌ Nothing to Skip",
                    "I'm not playing anything.",
                ),
                ephemeral=True,
            )