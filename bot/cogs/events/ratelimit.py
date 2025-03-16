import logging
import nextcord
from nextcord.ext import commands

from bot.databases import GuildDateBases
from bot.misc import utils

from bot.misc.lordbot import LordBot

_log = logging.getLogger(__name__)


class RateLimitEvent(commands.Cog):
    def __init__(self, bot: LordBot) -> None:
        self.bot = bot
        super().__init__()

    @commands.Cog.listener()
    async def on_http_ratelimit(self, limit: int, remaining: int, reset_after: float, bucket: str, scope: str):
        _log.debug('The bot received a rate limit of %s for %d out of %d service requests %s repeat after %.2f.', bucket, limit, remaining, scope, reset_after)

    @commands.Cog.listener()
    async def on_global_http_ratelimit(self, retry_after: float):
        _log.debug('The bot received a global rate limit of %.2f', retry_after)


def setup(bot):
    bot.add_cog(RateLimitEvent(bot))
