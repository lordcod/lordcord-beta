import time
import nextcord
from nextcord.ext import commands

from bot.databases import GuildDateBases
from bot.languages import i18n
from bot.misc.lordbot import LordBot
from bot.misc.time_transformer import display_time
from bot.misc.utils import translate_to_timestamp, randquan


class Reminder(commands.Cog):
    def __init__(self, bot: LordBot):
        self.bot = bot

    @commands.command()
    async def reminder(self, ctx: commands.Context, time_now: translate_to_timestamp, *, text: str) -> None:
        gdb = GuildDateBases(ctx.guild.id)
        locale = await gdb.get('language')

        if time.time() > time_now:
            await ctx.send(i18n.t(locale, 'reminder.error.time'))
            return
        self.bot.lord_handler_timer.create(
            time_now-time.time(),
            self.process_reminder(time.time(), ctx.author, ctx.channel, text),
            f"reminder:{ctx.guild.id}:{ctx.author.id}:{time_now :.0f}:{randquan(17)}"
        )
        await ctx.send(f"🛎️ OK, I'll mention you here on <t:{time_now :.0f}:f> (<t:{time_now :.0f}:R>)")

    async def process_reminder(self, time_old: float, member: nextcord.Member, channel: nextcord.TextChannel, text: str) -> None:
        gdb = GuildDateBases(channel.guild.id)
        locale = await gdb.get('language')
        color = await gdb.get('color')

        embed = nextcord.Embed(
            title=i18n.t(locale, 'reminder.embed.title'),
            description=i18n.t(locale, 'reminder.embed.description', time=display_time(time.time()-time_old)),
            color=color
        )
        embed.add_field(
            name=i18n.t(locale, 'reminder.embed.field'),
            value=text
        )

        await channel.send(member.mention, embed=embed)


def setup(bot):
    bot.add_cog(Reminder(bot))
