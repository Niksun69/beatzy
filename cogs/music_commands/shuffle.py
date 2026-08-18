import discord
from discord import app_commands
import random
from utils.voice import get_queue, save_queue_to_db
from utils.embed import success_embed, error_embed

class ShuffleMixin:
    @app_commands.command(name="shuffle", description="Shuffle the current queue")
    async def shuffle(self, interaction: discord.Interaction):
        guild_id = interaction.guild.id
        queue = get_queue(guild_id)
        if len(queue) < 2:
            await interaction.response.send_message(
                embed=error_embed("❌ Cannot Shuffle", "Not enough tracks in the queue to shuffle."),
                ephemeral=True
            )
            return
        random.shuffle(queue)
        save_queue_to_db(guild_id)
        await interaction.response.send_message(
            embed=success_embed("🔀 Shuffled", f"Queue shuffled! ({len(queue)} tracks)")
        )