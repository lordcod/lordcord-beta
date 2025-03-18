import logging
import time
import nextcord
from nextcord.ext import commands

from bot.databases import GuildDateBases, EconomyMemberDB, localdb
from bot.misc.lordbot import LordBot

_log = logging.getLogger(__name__)


class GuildsEvent(commands.Cog):
    def __init__(self, bot: LordBot) -> None:
        self.bot = bot
        super().__init__()

    @commands.Cog.listener()
    async def on_guild_available(self, guild: nextcord.Guild):
        gdb = GuildDateBases(guild.id)
        self.bot.lord_handler_timer.close(f'guild-deleted:{guild.id}')

        twitch_data = await gdb.get('twitch_notification', {})
        for data in twitch_data.values():
            await self.bot.twnoti.add_channel(guild.id, data['username'])

        youtube_data = await gdb.get('youtube_notification', {})
        for data in youtube_data.values():
            await self.bot.ytnoti.add_channel(guild.id, data['yt_id'])

    @commands.Cog.listener()
    async def on_guild_join(self, guild: nextcord.Guild):
        self.bot.lord_handler_timer.close(f'guild-deleted:{guild.id}')
        gdb = GuildDateBases(guild.id)
        await gdb.set('delete_task', None)

    @commands.Cog.listener()
    async def on_guild_remove(self, guild: nextcord.Guild):
        gdb = GuildDateBases(guild.id)
        delay = 60 * 60 * 24 * 3
        await gdb.set('delete_task', int(time.time()+delay))
        self.bot.lord_handler_timer.create(
            delay, gdb.delete(), f'guild-deleted:{guild.id}')


def setup(bot):
    bot.add_cog(GuildsEvent(bot))
