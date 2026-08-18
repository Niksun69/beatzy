from discord.ext import commands

from .game_commands.lol import LolMixin

class Games(
    LolMixin,
    commands.Cog
):
    def __init__(self, bot):
        self.bot = bot

        super().__init__()

async def setup(bot):
    await bot.add_cog(Games(bot))