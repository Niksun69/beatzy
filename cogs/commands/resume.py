import discord
from discord import app_commands
from utils.embed import error_embed, info_embed

class ResumeMixin:
    @app_commands.command(name="resume", description="Resume playback")
    async def resume(
        self,
        interaction: discord.Interaction,
    ):

        vc = interaction.guild.voice_client

        if vc and vc.is_paused():

            self.resume_track(
                interaction.guild.id
            )

            vc.resume()

            await interaction.response.send_message(
                embed=info_embed(
                    "▶️ Resumed",
                    "Playback has resumed.",
                )
            )

        else:

            await interaction.response.send_message(
                embed=error_embed(
                    "❌ Cannot Resume",
                    "I'm not currently paused.",
                ),
                ephemeral=True,
            )