import discord
from discord import ui

from utils.embed import queue_embed

# ========================================================
# Queue
# ========================================================

class QueueView(ui.View):
    def __init__(self, queue, page=0, per_page=10, thumbnail=None):
        super().__init__(timeout=120)
        self.queue = queue
        self.page = page
        self.per_page = per_page
        self.thumbnail = thumbnail
        self.total_pages = max(1, (len(queue) + per_page - 1) // per_page)

        # The two buttons are automatically added by the decorators below.
        # We'll add a select menu only if there are between 2 and 25 pages.
        if 2 <= self.total_pages <= 25:
            options = [discord.SelectOption(label=f"Page {i+1}", value=str(i)) for i in range(self.total_pages)]
            select = ui.Select(placeholder="Jump to page", options=options)
            select.callback = self.select_callback
            self.add_item(select)

        # Initial button states
        self.update_buttons()

    def update_buttons(self):
        # Find the buttons by their label (since we know them)
        for child in self.children:
            if isinstance(child, ui.Button):
                if child.label == '◀ Previous':
                    child.disabled = (self.page <= 0)
                elif child.label == 'Next ▶':
                    child.disabled = (self.page >= self.total_pages - 1)

    def get_embed(self):
        return queue_embed(self.queue, page=self.page, per_page=self.per_page, thumbnail=self.thumbnail)

    @ui.button(label='◀ Previous', style=discord.ButtonStyle.primary)
    async def previous_button(self, interaction: discord.Interaction, button: ui.Button):
        if self.page > 0:
            self.page -= 1
            self.update_buttons()
            await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @ui.button(label='Next ▶', style=discord.ButtonStyle.primary)
    async def next_button(self, interaction: discord.Interaction, button: ui.Button):
        if self.page < self.total_pages - 1:
            self.page += 1
            self.update_buttons()
            await interaction.response.edit_message(embed=self.get_embed(), view=self)

    async def select_callback(self, interaction: discord.Interaction):
        self.page = int(interaction.data['values'][0])
        self.update_buttons()
        embed = self.get_embed()
        await interaction.response.edit_message(embed=embed, view=self)