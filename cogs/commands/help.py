import discord
from discord import app_commands

class HelpMixin:
    @app_commands.command(name="help", description="Show all available commands and how to use them")
    async def help_command(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🎵 Music Bot Help",
            description="Here are all the commands you can use:",
            color=discord.Color.blurple()
        )

        commands_info = [
            ("/play", "Play a track, playlist, or resume the queue", "`/play` – resumes the queue\n`/play <query>` – plays a song or adds it to the queue\n`/play <URL>` – plays a YouTube video or playlist"),
            ("/skip", "Skip the currently playing track", "`/skip` – skips the current track and plays the next one"),
            ("/pause", "Pause the current track", "`/pause` – pauses playback"),
            ("/resume", "Resume the paused track", "`/resume` – resumes playback"),
            ("/stop", "Stop playback (keeps the queue)", "`/stop` – stops the current track, but the queue remains intact"),
            ("/leave", "Disconnect the bot from voice (keeps the queue)", "`/leave` – leaves the voice channel, preserving the queue"),
            ("/clear", "Clear the entire queue", "`/clear` – removes all tracks from the queue (does not stop playback)"),
            ("/queue", "Show the current queue with pagination", "`/queue` – displays the queue with interactive buttons to browse"),
            ("/shuffle", "Shuffle the current queue", "`/shuffle` – randomizes the order of all upcoming tracks"),
            ("/now", "Show currently playing track", "`/now` – shows the track currently being played with progress"),
            ("/help", "Show this help message", "`/help` – displays this help embed")
        ]

        for name, description, usage in commands_info:
            embed.add_field(
                name=name,
                value=f"*{description}*\n{usage}",
                inline=False
            )

        embed.set_footer(text="Use /play <query> to get started! | Public Alcohol Inspector")
        await interaction.response.send_message(embed=embed)