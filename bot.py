import discord
from discord.ext import commands
from config import DISCORD_TOKEN, DISCORD_ID
from utils.voice import load_queues_from_db

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Test server ID
TEST_GUILD_ID = DISCORD_ID

@bot.event
async def on_ready():
    load_queues_from_db()
    print(f"Logged in as {bot.user}")
    # Sync globaly
    # await bot.tree.sync()
    # print(f"Synced commands to guild {TEST_GUILD_ID}")

@bot.tree.command(name="sync", description="Sync commands globally or to test guild (owner only)")
@commands.is_owner()
async def sync_global(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    
    guild = discord.Object(id=TEST_GUILD_ID)
    try:
        # Try to sync to the test guild first (instant)
        await bot.tree.sync(guild=guild)
        await interaction.followup.send(f"Commands synced to guild {TEST_GUILD_ID}.", ephemeral=True)
    except discord.Forbidden:
        # If that fails, fall back to global sync (slower, but doesn't need guild permissions)
        await bot.tree.sync()
        await interaction.followup.send(
            "Could not sync to the test guild (missing `applications.commands` permission?).\n"
            "Synced globally instead – changes may take up to an hour to appear.",
            ephemeral=True
        )
    except Exception as e:
        await interaction.followup.send(f"Sync failed: {e}", ephemeral=True)

async def load_extensions():
    await bot.load_extension("cogs.music")

@bot.event
async def setup_hook():
    await load_extensions()

if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)