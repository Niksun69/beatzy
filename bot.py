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

    await bot.tree.sync()
    print("Commands synced globally.")
    # # Optionally also sync to guild
    # guild = discord.Object(id=TEST_GUILD_ID)
    # await bot.tree.sync(guild=guild)
    # print(f"Commands synced to guild {TEST_GUILD_ID}.")

@bot.tree.command(name="sync", description="Sync commands (owner only)")
@commands.is_owner()
async def sync_global(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    
    # Sync to test guild
    guild = discord.Object(id=TEST_GUILD_ID)
    try:
        # Copy global commands to guild (if any)
        bot.tree.copy_global_to(guild=guild)
        # Then sync
        await bot.tree.sync(guild=guild)
        await interaction.followup.send(f"✅ Commands synced to guild {TEST_GUILD_ID}.", ephemeral=True)
    except discord.Forbidden:
        await bot.tree.sync()
        await interaction.followup.send("Synced globally.", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"Sync failed: {e}", ephemeral=True)

@bot.tree.command(name="listcommands", description="List all registered slash commands (owner only)")
@commands.is_owner()
async def list_commands(interaction: discord.Interaction):
    commands_list = [cmd.name for cmd in bot.tree.get_commands()]
    await interaction.response.send_message(f"Registered commands: {', '.join(commands_list)}", ephemeral=True)

@bot.tree.command(name="reload", description="Reload music cog (owner only)")
@commands.is_owner()
async def reload_cog(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    await bot.reload_extension("cogs.music")
    await interaction.followup.send("✅ Cog reloaded.", ephemeral=True)

async def load_extensions():
    await bot.load_extension("cogs.music")
    await bot.load_extension("cogs.games")

@bot.event
async def setup_hook():
    await load_extensions()

if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)