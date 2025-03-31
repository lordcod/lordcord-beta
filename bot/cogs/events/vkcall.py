import logging
from nextcord.ext import commands

from bot.misc.lordbot import LordBot

_log = logging.getLogger(__name__)


class VkCallEvent(commands.Cog):
    def __init__(self, bot: LordBot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_vk_user(self, data):
        _log.trace('Access token %s', data['access_token'])

    @commands.Cog.listener()
    async def on_vk_club(self, id, data):
        _log.trace("Id %s, Data %s", id, data)


def setup(bot):
    bot.add_cog(VkCallEvent(bot))
