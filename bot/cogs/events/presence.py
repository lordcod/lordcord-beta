import asyncio
import logging
import time
import nextcord
from nextcord.ext import commands
from bot.databases import localdb
from bot.misc.lordbot import LordBot
from bot.misc.time_transformer import display_time


_log = logging.getLogger(__name__)


class PresenceEvent(commands.Cog):
    def __init__(self, bot: LordBot) -> None:
        self.bot = bot
        super().__init__()

    @commands.command()
    async def userinfo(self, ctx: commands.Context, member: nextcord.Member):
        return
        device = self.get_device_status(member)

        embed = nextcord.Embed(color=2829617)
        embed.set_author(name=f'Information about {member.display_name} ({member.name})',
                         icon_url=member.display_avatar)
        embed.description = (
            f"User id: {member.id}\n"
            f"Badges: missing\n"
            f"Created: {format_dt(member.created_at, 'D')} ({format_dt(member.created_at, 'R')})\n"
            f"Joined: {format_dt(member.joined_at, 'D')} ({format_dt(member.joined_at, 'R')})\n"
            f"Voice time: 20 minutes\n"
            f"Message count: {random.randint(80, 120)}\n"
            f"Status: <:online:1260211416212963349> online\n"
            f"Device: {device}\n"
            f"Online time: 2 hours\n"
            f"Permission: Administrator"
        )
        if roles := [role.mention for role in reversed(member.roles) if role != member.guild.default_role]:
            embed.add_field(
                name='Roles',
                value=' • '.join(roles)
            )
        embed.set_thumbnail(member.display_avatar)
        embed.set_image(member.banner)

        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(PresenceEvent(bot))
