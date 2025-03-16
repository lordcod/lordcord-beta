import asyncio
from typing import Optional
import nextcord
from nextcord.ext import commands

from bot.databases import GuildDateBases
from bot.misc import utils

from bot.misc.lordbot import LordBot


class ThreadEvent(commands.Cog):
    def __init__(self, bot: LordBot) -> None:
        self.bot = bot
        super().__init__()

    @commands.Cog.listener()
    async def on_thread_create(self, thread: nextcord.Thread):
        guild_data = GuildDateBases(thread.guild.id)

        afm = await guild_data.get('thread_messages')
        message_data = afm.get(thread.parent_id)

        afr = await guild_data.get('thread_roles')
        roles_data = afr.get(thread.parent_id)

        asyncio.create_task(self.send_message(thread, message_data))
        asyncio.create_task(self.add_roles(thread, roles_data))

    async def send_message(self, thread: nextcord.Thread, data: Optional[dict]):
        if not data:
            return

        content = utils.generate_message(data)
        await thread.send(**content)

    def check_perm(self, item: Optional[nextcord.Role]) -> bool:
        if item is None:
            return False
        return item.is_assignable()

    async def add_roles(self, thread: nextcord.Thread, data: Optional[list]):
        if not data:
            return

        roles = filter(
            self.check_perm,
            map(thread.guild.get_role, data)
        )
        await thread.owner.add_roles(*roles)


def setup(bot):
    bot.add_cog(ThreadEvent(bot))
