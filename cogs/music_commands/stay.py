import asyncio
import discord
from discord import app_commands
from utils.embed import success_embed, info_embed, error_embed
from utils.voice import get_queue

class StayMixin:
    @app_commands.command(name="247", description="Toggle 24/7 mode (bot stays in voice indefinitely).")
    async def stay_command(self, interaction: discord.Interaction):
        guild_id = interaction.guild.id
        current = self.stay_connected.get(guild_id, False)
        new_state = not current

        # ----------------------------------------------------
        # Enabling 24/7
        # ----------------------------------------------------
        if new_state:
            # Cancel any pending idle timer
            if guild_id in self.idle_timer:
                self.idle_timer[guild_id].cancel()
                self.idle_timer.pop(guild_id, None)

            # If not connected, try to join the user's voice channel
            vc = interaction.guild.voice_client
            if vc is None:
                if not interaction.user.voice:
                    await interaction.response.send_message(
                        embed=error_embed(
                            "❌ Not in Voice",
                            "You must be in a voice channel to enable 24/7 mode."
                        ),
                        ephemeral=True,
                    )
                    return
                try:
                    channel = interaction.user.voice.channel
                    await channel.connect()
                    vc = interaction.guild.voice_client
                except Exception as e:
                    await interaction.response.send_message(
                        embed=error_embed(
                            "❌ Connection Failed",
                            f"Could not join your voice channel: {e}"
                        ),
                        ephemeral=True,
                    )
                    return

            # Mark 24/7 as enabled
            self.stay_connected[guild_id] = True

            status = "enabled 🔛"
            description = "I will now stay in the voice channel even when the queue is empty."

        # ----------------------------------------------------
        # Disabling 24/7
        # ----------------------------------------------------
        else:
            self.stay_connected[guild_id] = False

            # If nothing is playing, start the idle timer
            vc = interaction.guild.voice_client
            if vc and not (vc.is_playing() or vc.is_paused()):
                if not get_queue(guild_id):
                    if guild_id in self.idle_timer:
                        self.idle_timer[guild_id].cancel()
                    self.idle_timer[guild_id] = asyncio.create_task(self._idle_timeout(guild_id))

            status = "disabled 🔕"
            description = "I will now disconnect after 60 seconds of inactivity."

        await interaction.response.send_message(
            embed=success_embed("🔄 24/7 Mode", f"24/7 mode has been **{status}**.\n{description}")
        )