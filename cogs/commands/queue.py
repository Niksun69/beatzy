import discord
from discord import app_commands
from utils.embed import error_embed
from utils.ui import QueueView
from utils.voice import get_queue

class QueueMixin:
    @app_commands.command(name="queue", description="Show the current queue")
    async def queue(self, interaction: discord.Interaction):
        queue = get_queue(interaction.guild.id)
        if not queue:
            embed = error_embed("❌ Queue Empty", "There are no tracks in the queue.")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Create view with initial page 0
        view = QueueView(queue, page=0, per_page=10)
        embed = view.get_embed()
        await interaction.response.send_message(embed=embed, view=view)