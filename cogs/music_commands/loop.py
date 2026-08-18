import discord
from discord import app_commands
from utils.embed import success_embed, info_embed

class LoopMixin:
    @app_commands.command(name="loop", description="Toggle looping of the current track (repeat one).")
    async def loop(self, interaction: discord.Interaction):
        guild_id = interaction.guild.id
        new_state = not self.loop_enabled.get(guild_id, False)
        self.loop_enabled[guild_id] = new_state

        if new_state:
            # If we have a current track, store it as loop track
            vc = interaction.guild.voice_client
            if vc and (vc.is_playing() or vc.is_paused()):
                from utils.voice import get_current_track
                track = get_current_track(guild_id)
                if track:
                    self.loop_track[guild_id] = track
            await interaction.response.send_message(
                embed=success_embed("🔁 Loop Enabled", "The current track will repeat indefinitely.")
            )
        else:
            self.loop_track.pop(guild_id, None)   # clear loop track
            await interaction.response.send_message(
                embed=success_embed("🔁 Loop Disabled", "Looping is now off.")
            )