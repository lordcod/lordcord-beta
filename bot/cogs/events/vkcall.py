import nextcord
from nextcord.ext import commands

from bot.misc.lordbot import LordBot


class VkCallEvent(commands.Cog):
    def __init__(self, bot: LordBot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_vk_user(self, data):
        print(data)


def setup(bot):
    bot.add_cog(VkCallEvent(bot))
