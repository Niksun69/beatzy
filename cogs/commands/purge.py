import discord
from discord import app_commands

class PurgeMixin:
    @app_commands.command(name="purge", description="Delete the bot's messages in this channel.")
    async def purge(self, interaction: discord.Interaction, count: int = 10):
        """
        Deletes a specified number of messages sent by the bot.
        """
        # Clamp count between 1 and 100
        count = min(max(1, count), 100)

        # Defer the response so we don't time out
        await interaction.response.defer(ephemeral=True)

        # Collect bot messages from the channel history
        bot_messages = []
        # We scan up to 2x the requested count to ensure we gather enough bot messages
        async for msg in interaction.channel.history(limit=count * 2):
            if msg.author == interaction.client.user:
                bot_messages.append(msg)
                if len(bot_messages) >= count:
                    break

        if not bot_messages:
            await interaction.followup.send("No bot messages found to delete.", ephemeral=True)
            return

        # Bulk delete (Discord allows up to 100 messages at once)
        try:
            await interaction.channel.delete_messages(bot_messages)
            await interaction.followup.send(f"Deleted {len(bot_messages)} bot message(s).", ephemeral=True)
        except discord.HTTPException as e:
            await interaction.followup.send(f"Failed to delete messages: {e}", ephemeral=True)