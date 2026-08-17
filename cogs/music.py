from discord.ext import commands

from utils.helper import MusicHelpers

from .commands.play import PlayMixin
from .commands.skip import SkipMixin
from .commands.pause import PauseMixin
from .commands.resume import ResumeMixin
from .commands.stop import StopMixin
from .commands.skip import SkipMixin
from .commands.clear import ClearMixin
from .commands.leave import LeaveMixin
from .commands.now import NowMixin
from .commands.shuffle import ShuffleMixin
from .commands.queue import QueueMixin
from .commands.help import HelpMixin
from .commands.purge import PurgeMixin
from .commands.stay import StayMixin
from .commands.loop import LoopMixin
from .commands.about import AboutMixin


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
    await bot.add_cog(
        Music(bot)
    )