import nextcord
from nextcord.ext import commands

from bot.misc import logstool
from bot.misc.lordbot import LordBot


class RolesEvent(commands.Cog):
    def __init__(self, bot: LordBot) -> None:
        self.bot = bot
        super().__init__()

    @commands.Cog.listener()
    async def on_member_update(self, before: nextcord.Member, after: nextcord.Member):
        removed_roles = set(before.roles)-set(after.roles)
        added_roles = set(after.roles)-set(before.roles)
        if removed_roles:
            role = list(removed_roles)[0]
            await logstool.pre_remove_role(after, role)
        if added_roles:
            role = list(added_roles)[0]
            await logstool.pre_add_role(after, role)


def setup(bot):
    bot.add_cog(RolesEvent(bot))
