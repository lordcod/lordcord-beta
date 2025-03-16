import nextcord
from nextcord.ext import commands
import time

from bot.databases import localdb
from bot.misc.lordbot import LordBot


class MemberTimeoutEvent(commands.Cog):
    def __init__(self, bot: LordBot) -> None:
        self.bot = bot
        super().__init__()

    @commands.Cog.listener()
    async def on_guild_audit_log_entry_create(self,
                                              entry: nextcord.AuditLogEntry):
        if not (entry.action == nextcord.AuditLogAction.member_update
                and hasattr(entry.before, "communication_disabled_until")):
            return

        guild_id = entry.guild.id
        user_id = entry.target.id
        timeout_db = await localdb.get_table('timeout')
        timeout_data = await timeout_db.get(guild_id, {})
        loctime = time.time()

        if (entry.before.communication_disabled_until is None and
                entry.after.communication_disabled_until is not None):

            mute_time = entry.target.communication_disabled_until.timestamp()
            duration = mute_time-loctime

            self.bot.dispatch(
                "timeout", entry.target, duration, entry.user, entry.reason)

            self.bot.lord_handler_timer.create(
                duration,
                self.process_untimeout(entry.target),
                f'timeout:{guild_id}:{user_id}'
            )

            timeout_data[user_id] = (loctime, mute_time, duration)
            await timeout_db.set(guild_id, timeout_data)
        if (entry.before.communication_disabled_until is not None and
                entry.after.communication_disabled_until is None):
            try:
                data = timeout_data[user_id]
                duration = data[2]
                self.bot.lord_handler_timer.close(f'timeout:{guild_id}:{entry.user.id}')
            except (KeyError, IndexError, AttributeError):
                duration = None

            self.bot.dispatch("untimeout", entry.target,
                              duration, entry.user, entry.reason)

            timeout_data.pop(user_id, None)
            await timeout_db.set(guild_id, timeout_data)

    async def process_untimeout(self, member: nextcord.Member):
        timeout_db = await localdb.get_table('timeout')
        timeout_data = await timeout_db.get(member.guild.id, {})

        try:
            data = timeout_data[member.id]
            duration = data[2]
        except (KeyError, IndexError):
            duration = None

        timeout_data.pop(member.id, None)
        await timeout_db.set(member.guild.id, timeout_data)

        setattr(member, '_timeout', None)
        self.bot.dispatch("untimeout", member, duration, None, None)

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        timeout_db = await localdb.get_table('timeout')

        for guild_id, data in (await timeout_db.fetch()).items():
            guild = self.bot.get_guild(guild_id)

            if guild is None:
                continue

            for user_id, timeout_data in data.items():
                member = guild.get_member(user_id)

                if member is None:
                    continue

                data = timeout_data[user_id]
                mute_time = data[1]
                self.bot.lord_handler_timer.create(
                    mute_time-time.time(),
                    self.process_untimeout(member),
                    f'timeout:{guild_id}:{user_id}'
                )


def setup(bot):
    bot.add_cog(MemberTimeoutEvent(bot))
