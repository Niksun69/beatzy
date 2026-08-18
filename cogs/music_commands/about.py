import discord
from discord import app_commands

class AboutMixin:
    @app_commands.command(name="about", description="About this bot – credits and source.")
    async def about_command(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🎵 Beatzy",
            description=(
                "A feature-rich music bot for Discord, built with Python.\n\n"
                "**Made by** [Nikola](https://artisticcode.dev)\n"
                "**Website** [artisticcode.dev](https://artisticcode.dev)\n"
                "**Source Code** Open-source and self-hosted.\n"
                "**GitHub** [github.com/yourusername/pymusicbot](https://github.com/yourusername/beatzy)\n\n"
                "This bot is self-hosted – you can run your own instance!"
            ),
            color=discord.Color.blue()
        )
        embed.set_footer(text="Powered by discord.py and yt-dlp")
        # embed.set_thumbnail(url="https://artisticcode.dev/logo.png")

        await interaction.response.send_message(embed=embed)