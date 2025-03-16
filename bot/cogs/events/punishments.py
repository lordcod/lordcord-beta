
import nextcord
from nextcord.ext import commands
from typing import Optional

from bot.misc import logstool
from bot.misc.lordbot import LordBot


class PunishmentsEvent(commands.Cog):
    def __init__(self, bot: LordBot) -> None:
        self.bot = bot
        super().__init__()

    @commands.Cog.listener()
    async def on_guild_audit_log_entry_create(self, entry: nextcord.AuditLogEntry):
        if entry.action not in {nextcord.AuditLogAction.ban,  nextcord.AuditLogAction.unban, nextcord.AuditLogAction.kick}:
            return

        # global -> local
        get_user = entry._state.get_user
        wrap = getattr(logstool.Logs(entry.guild), entry.action.name, None)
        await wrap(
            entry.guild,
            get_user(int(entry._target_id)),
            entry.user,
            entry.reason
        )

    @commands.Cog.listener()
    async def on_timeout(self,
                         member: nextcord.Member,
                         duration: int,
                         moderator: nextcord.Member,
                         reason: Optional[str] = None):
        await logstool.Logs(member.guild).timeout(member, duration, moderator, reason)

    @commands.Cog.listener()
    async def on_untimeout(self,
                           member: nextcord.Member,
                           duration: Optional[int] = None,
                           moderator: Optional[nextcord.Member] = None,
                           reason: Optional[str] = None):
        await logstool.Logs(member.guild).untimeout(member, duration, moderator, reason)


def setup(bot):
    bot.add_cog(PunishmentsEvent(bot))
