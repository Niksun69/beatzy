import discord
from discord import app_commands
from utils.embed import error_embed, success_embed
from utils.voice import get_queue, save_queue_to_db

class ClearMixin:
    @app_commands.command(name="clear", description="Clear the queue without stopping playback")
    async def clear(
        self,
        interaction: discord.Interaction,
    ):

        guild_id = interaction.guild.id

        queue = get_queue(guild_id)

        if queue:

            queue.clear()

            save_queue_to_db(
                guild_id
            )

            await interaction.response.send_message(
                embed=success_embed(
                    "🧹 Queue Cleared",
                    "All queued tracks were removed.",
                )
            )

        else:

            await interaction.response.send_message(
                embed=error_embed(
                    "❌ Queue Empty",
                    "There are no tracks in the queue.",
                ),
                ephemeral=True,
            )