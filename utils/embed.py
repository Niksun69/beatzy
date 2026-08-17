import time
import discord

from utils.voice import (
    get_queue,
    clear_queue,
    save_queue_to_db,
)


# ============================================================
# COLORS
# ============================================================

NOW_PLAYING_COLOR = discord.Color.from_rgb(255, 193, 7)
INFO_COLOR = discord.Color.blurple()
SUCCESS_COLOR = discord.Color.green()
ERROR_COLOR = discord.Color.red()


# ============================================================
# GENERAL EMBEDS
# ============================================================

def info_embed(title, description, color=INFO_COLOR):
    return discord.Embed(
        title=title,
        description=description,
        color=color,
    )


def success_embed(title, description):
    return discord.Embed(
        title=title,
        description=description,
        color=SUCCESS_COLOR,
    )


def error_embed(title, description):
    return discord.Embed(
        title=title,
        description=description,
        color=ERROR_COLOR,
    )


# ============================================================
# TIME HELPERS
# ============================================================

def format_duration(seconds):
    """
    Format seconds into:
        00:00
        04:37
        01:24:31
    """

    try:
        seconds = max(0, int(seconds or 0))
    except (TypeError, ValueError):
        seconds = 0

    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    return f"{minutes:02d}:{seconds:02d}"


# ============================================================
# PROGRESS BAR
# ============================================================

def progress_bar(elapsed, duration, bar_length=24):
    """
    Creates a clean Discord-friendly progress bar.

    Example:
        ▶ ━━━━━━━━━●━━━━━━━━━━━━ 02:14 / 04:37

    Live streams:
        🔴 LIVE
    """

    try:
        elapsed = max(0.0, float(elapsed or 0))
    except (TypeError, ValueError):
        elapsed = 0.0

    try:
        duration = float(duration or 0)
    except (TypeError, ValueError):
        duration = 0.0

    if duration <= 0:
        return "🔴 **LIVE**"

    progress = max(0.0, min(elapsed / duration, 1.0))

    # Keep the playhead inside the bar.
    position = round(progress * (bar_length - 1))

    bar = ""

    for index in range(bar_length):
        if index == position:
            bar += "●"
        else:
            bar += "━"

    elapsed_text = format_duration(elapsed)
    duration_text = format_duration(duration)

    return (
        f"▶ `{bar}`\n"
        f"`{elapsed_text}`　　　　　　　　　　　　　　　　　`{duration_text}`"
    )


# ============================================================
# SOURCE / PLATFORM
# ============================================================

def detect_platform(url):
    """
    Detect the platform from the original URL.
    """

    if not url:
        return "🎵 Music"

    url = url.lower()

    if "youtube.com" in url or "youtu.be" in url:
        return "▶️ YouTube"

    if "spotify.com" in url:
        return "🟢 Spotify"

    if "soundcloud.com" in url:
        return "🟠 SoundCloud"

    if "twitch.tv" in url:
        return "🟣 Twitch"

    return "🎵 Direct Audio"


# ============================================================
# TITLE CLEANUP
# ============================================================

def clean_title(title, max_length=256):
    """
    Prevent extremely long titles from making the embed ugly.
    """

    if not title:
        return "Unknown Track"

    title = str(title).strip()

    if len(title) <= max_length:
        return title

    return title[: max_length - 3] + "..."


# ============================================================
# NOW PLAYING EMBED
# ============================================================

def now_playing_with_progress(
    title,
    url,
    thumbnail,
    elapsed,
    duration,
    queue_count=0,
    paused=False,
    requester=None,
):
    """
    Creates the main Now Playing card.

    This is intentionally kept compatible with your existing
    _play_song() and /now command.
    """

    title = clean_title(title)

    platform = detect_platform(url)

    # --------------------------------------------------------
    # Status
    # --------------------------------------------------------

    if paused:
        status = "⏸️ **PAUSED**"
        color = discord.Color.orange()
    else:
        status = "🎶 **PLAYING**"
        color = NOW_PLAYING_COLOR

    # --------------------------------------------------------
    # Embed
    # --------------------------------------------------------

    embed = discord.Embed(
        title="🎵  NOW PLAYING",
        description=(
            f"### {title}\n"
            f"{status}"
        ),
        color=color,
    )

    # --------------------------------------------------------
    # Thumbnail
    # --------------------------------------------------------

    if thumbnail:
        embed.set_thumbnail(url=thumbnail)

    # --------------------------------------------------------
    # Progress
    # --------------------------------------------------------

    embed.add_field(
        name="‎",
        value=progress_bar(
            elapsed,
            duration,
            bar_length=24,
        ),
        inline=False,
    )

    # --------------------------------------------------------
    # Metadata row
    # --------------------------------------------------------

    embed.add_field(
        name="SOURCE",
        value=platform,
        inline=True,
    )

    if duration and duration > 0:
        duration_text = format_duration(duration)
    else:
        duration_text = "Live"

    embed.add_field(
        name="DURATION",
        value=f"⏱️ `{duration_text}`",
        inline=True,
    )

    embed.add_field(
        name="QUEUE",
        value=f"📋 `{queue_count}` upcoming",
        inline=True,
    )

    # --------------------------------------------------------
    # URL
    # --------------------------------------------------------

    if url:
        embed.add_field(
            name="🔗 Open Track",
            value=f"[Click here to open the track]({url})",
            inline=False,
        )

    # --------------------------------------------------------
    # Footer
    # --------------------------------------------------------

    footer_parts = [
        "Music Player",
        platform,
    ]

    if requester:
        footer_parts.append(f"Requested by {requester}")

    embed.set_footer(
        text=" • ".join(footer_parts)
    )

    return embed


# ============================================================
# QUEUE EMBED
# ============================================================

def queue_embed(queue, page=0, per_page=10, thumbnail=None):
    total = len(queue)
    start = page * per_page
    end = min(start + per_page, total)
    
    embed = discord.Embed(
        title="🎵 Queue",
        description=f"Showing {start+1}-{end} of {total} tracks",
        color=discord.Color.green()
    )
    
    if total == 0:
        embed.description = "The queue is empty."
        return embed

    # add a thumbnail of the first track (or current track)
    if thumbnail:
        embed.set_thumbnail(url=thumbnail)

    for i, track in enumerate(queue[start:end], start=start+1):
        title = track.get('title', 'Unknown')
        duration = track.get('duration', 0)
        dur_str = format_duration(duration) if duration and duration > 0 else "Live"
        # Build a nice field with duration
        embed.add_field(
            name=f"{i}. {title}",
            value=f"⏱️ `{dur_str}`",
            inline=False
        )
    
    # Add footer with total duration (optional)
    total_duration = sum(t.get('duration') or 0 for t in queue)
    if total_duration > 0:
        embed.set_footer(text=f"Total duration: {format_duration(total_duration)}")
    
    return embed


# ============================================================
# MUSIC CONTROL VIEW
# ============================================================

class MusicControlView(discord.ui.View):

    def __init__(self, cog, guild_id):
        super().__init__(timeout=None)

        self.cog = cog
        self.guild_id = guild_id

        self.paused = False

        # Configure initial state.
        self._update_pause_button()

    # --------------------------------------------------------
    # Pause / Resume button
    # --------------------------------------------------------

    @discord.ui.button(
        label="Pause",
        style=discord.ButtonStyle.secondary,
        emoji="⏸️",
        custom_id="music_pause_resume",
        row=0,
    )
    async def pause_resume_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        vc = interaction.guild.voice_client

        if not vc:
            await interaction.response.send_message(
                "I'm not connected to a voice channel.",
                ephemeral=True,
            )
            return

        # ----------------------------------------------------
        # Currently playing -> pause
        # ----------------------------------------------------

        if vc.is_playing():

            self.cog.pause_track(self.guild_id)

            vc.pause()

            self.paused = True
            self._update_pause_button()

            await interaction.response.edit_message(
                view=self
            )

            return

        # ----------------------------------------------------
        # Currently paused -> resume
        # ----------------------------------------------------

        if vc.is_paused():

            self.cog.resume_track(self.guild_id)

            vc.resume()

            self.paused = False
            self._update_pause_button()

            await interaction.response.edit_message(
                view=self
            )

            return

        await interaction.response.send_message(
            "Nothing is currently playing.",
            ephemeral=True,
        )

    # --------------------------------------------------------
    # Skip
    # --------------------------------------------------------

    @discord.ui.button(
        label="Skip",
        style=discord.ButtonStyle.primary,
        emoji="⏭️",
        custom_id="music_skip",
        row=0,
    )
    async def skip_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        vc = interaction.guild.voice_client

        if not vc or not (
            vc.is_playing() or vc.is_paused()
        ):
            await interaction.response.send_message(
                "Nothing to skip.",
                ephemeral=True,
            )
            return

        await interaction.response.defer()

        self.cog._cancel_update_task(self.guild_id)
        self.cog.skip_triggered[self.guild_id] = True

        vc.stop()

        await interaction.followup.send(
            embed=success_embed(
                "⏭️ Skipped",
                "The current track was skipped.",
            ),
            ephemeral=True,
        )

    # --------------------------------------------------------
    # Stop
    # --------------------------------------------------------

    @discord.ui.button(
        label="Stop",
        style=discord.ButtonStyle.danger,
        emoji="⏹️",
        custom_id="music_stop",
        row=0,
    )
    async def stop_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        vc = interaction.guild.voice_client

        if not vc:
            await interaction.response.send_message(
                "I'm not connected to a voice channel.",
                ephemeral=True,
            )
            return

        await interaction.response.defer()

        # Stop the update loop
        self.cog._cancel_update_task(self.guild_id)

        # Stop playback
        if vc.is_playing() or vc.is_paused():
            vc.stop()

        # Delete the Now Playing message from the channel
        msg = self.cog.current_messages.pop(self.guild_id, None)
        if msg:
            try:
                await msg.delete()
            except (discord.NotFound, discord.HTTPException):
                pass

        # Check if 24/7 mode is enabled
        if self.cog.stay_connected.get(self.guild_id, False):
            # 24/7 is on – stay connected
            await interaction.followup.send(
                embed=success_embed(
                    "⏹️ Playback Stopped",
                    "Playback stopped.\n"
                    "24/7 mode is active – I'll stay connected.\n"
                    "Use `/play` to resume the queue.",
                ),
                ephemeral=True,
            )
        else:
            # 24/7 is off – disconnect
            await vc.disconnect()
            await interaction.followup.send(
                embed=success_embed(
                    "⏹️ Playback Stopped",
                    "Stopped playback and left the voice channel.\n"
                    "The queue is still intact – use `/play` to resume.",
                ),
                ephemeral=True,
            )

    # --------------------------------------------------------
    # Queue
    # --------------------------------------------------------

    @discord.ui.button(
        label="Queue",
        style=discord.ButtonStyle.secondary,
        emoji="📋",
        custom_id="music_queue",
        row=0,
    )
    async def queue_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button,
    ):
        queue = get_queue(self.guild_id)

        embed = queue_embed(queue)

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True,
        )

    # --------------------------------------------------------
    # Helpers
    # --------------------------------------------------------

    def _update_pause_button(self):
        """
        Change the first button between Pause and Resume.
        """

        button = self.pause_resume_button

        if self.paused:
            button.label = "Resume"
            button.emoji = "▶️"
            button.style = discord.ButtonStyle.success

        else:
            button.label = "Pause"
            button.emoji = "⏸️"
            button.style = discord.ButtonStyle.secondary