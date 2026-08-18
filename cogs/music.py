from discord.ext import commands

from utils.helper import MusicHelpers

from .music_commands.play import PlayMixin
from .music_commands.skip import SkipMixin
from .music_commands.pause import PauseMixin
from .music_commands.resume import ResumeMixin
from .music_commands.stop import StopMixin
from .music_commands.skip import SkipMixin
from .music_commands.clear import ClearMixin
from .music_commands.leave import LeaveMixin
from .music_commands.now import NowMixin
from .music_commands.shuffle import ShuffleMixin
from .music_commands.queue import QueueMixin
from .music_commands.help import HelpMixin
from .music_commands.purge import PurgeMixin
from .music_commands.stay import StayMixin
from .music_commands.loop import LoopMixin
from .music_commands.about import AboutMixin


class Music(
    PlayMixin,
    SkipMixin,
    PauseMixin,
    ResumeMixin,
    StopMixin,
    LeaveMixin,
    ClearMixin,
    QueueMixin,
    NowMixin,
    ShuffleMixin,
    HelpMixin,
    PurgeMixin,
    StayMixin,
    LoopMixin,
    AboutMixin,
    MusicHelpers,
    commands.Cog
):
    def __init__(self, bot):
        self.bot = bot
        
        self.update_tasks = {}
        self.current_messages = {}
        self.current_views = {}
        self.paused_time = {}
        self.pause_started = {}
        self.idle_timer = {}
        self.play_start_time = {}
        self.stay_connected = {}
        self.loop_enabled = {}
        self.loop_track = {}
        self.skip_triggered = {}

        super().__init__()


async def setup(bot):
    await bot.add_cog(Music(bot))