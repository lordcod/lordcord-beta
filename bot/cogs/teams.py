import asyncio
import random
import string
import time
from typing import Literal, Optional
import nextcord
from nextcord.ext import commands

from bot.databases.datastore import cache
from bot.databases.handlers.economyHD import EconomyMemberDB
from bot.databases.models import EconomicModel
from bot.misc.lordbot import LordBot
from bot.misc.moderation import spam
from bot.resources import errors
from bot.resources.ether import Emoji


class Teams(commands.Cog):
    def __init__(self, bot: LordBot):
        self.bot = bot

    async def cog_check(self, ctx: commands.Context) -> bool:
        app_info = await self.bot.application_info()
        member_teams = [member.id for member in (
            app_info.team.members)] if app_info.team else [app_info.owner]
        if ctx.author.id not in member_teams:
            raise errors.OnlyTeamError(author=ctx.author)
        return True

    @commands.command()
    async def test_vk_verify(self, ctx: commands.Context):
        state = ''.join([random.choice(string.hexdigits) for _ in range(12)])
        await ctx.send(f'https://lordcord.xyz/server-select?state={state}')
        data = await self.bot.wait_api_state(state)
        await ctx.send(str(data))
        data = await self.bot.wait_api_state(state)
        await ctx.send(str(data))

    @commands.command()
    async def switch_command(self, ctx: commands.Context, flag: bool, *, cmd_name: str):
        cmd = nextcord.utils.get(self.bot.commands, qualified_name=cmd_name)
        if cmd is None:
            await ctx.message.add_reaction(Emoji.cross)
            return
        cmd.enabled = flag
        await ctx.message.add_reaction(Emoji.success)

    @commands.command()
    async def send_exc(self, ctx: commands.Context):
        raise TypeError("test exc")

    @commands.command()
    async def shutdown(self, ctx: commands.Context):
        await cache.close(close_connection_pool=True)
        await ctx.send("The bot has activated the completion process!")
        await self.bot.close()

    @commands.command()
    @commands.guild_only()
    async def sudo(
        self, ctx: commands.Context, member: nextcord.Member, *, command: str
    ):
        ctx.message.author = member
        await self.bot.process_with_str(ctx.message, command)

    @commands.command(aliases=['load_cog'])
    async def load_extension(self, ctx: commands.Context, name):
        self.bot.load_extension(f"bot.cogs.{name}")
        await ctx.send(f"Service **{name}** successfully enabled")

    @commands.command(aliases=['unload_cog'])
    async def unload_extension(self, ctx: commands.Context, name):
        if name == "teams":
            return

        self.bot.unload_extension(f"bot.cogs.{name}")
        await ctx.send(f"Service **{name}** successfully shut down")

    @commands.command(aliases=['reload_cog'])
    async def reload_extension(self, ctx: commands.Context, name):
        self.bot.reload_extension(f"bot.cogs.{name}")
        await ctx.send(f"The **{name}** service has been successfully reloaded!")

    @commands.command(aliases=['reload_cogs', 'reload_all_cogs'])
    async def reload_all_extensions(self, ctx: commands.Context):
        exts = self.bot.extensions
        for ext in exts.values():
            name = ext.__name__
            self.bot.reload_extension(name)

        await ctx.send("All services have been successfully restarted")

    @commands.command(aliases=['cogs'])
    async def extensions(self, ctx: commands.Context):
        exts = self.bot.extensions
        name_exts = [ext.__name__ for ext in exts.values()]
        string = "\n".join(name_exts)
        await ctx.send(string)

    @commands.command()
    async def sql_execute(
        self,
        ctx: commands.Context,
        *,
        query: str
    ):
        await self.bot.engine.execute(query)
        await ctx.message.add_reaction(Emoji.success)

    @commands.command(aliases=['notifi_info'])
    async def get_notifi_info(self, ctx: commands.Context):
        twnoti = self.bot.twnoti
        ytnoti = self.bot.ytnoti

        await ctx.send(
            'Notification is worked\n'
            f'Twitch: {twnoti.running} (<t:{twnoti.last_heartbeat:.0f}:R>)\n'
            f'Youtube: {ytnoti.running} (<t:{ytnoti.last_heartbeat:.0f}:R>)'
        )

    @commands.command()
    async def restart_notifi(self, ctx: commands.Context, service: Literal['twnoti', 'ytnoti']):
        noti = getattr(self.bot, service)
        noti.running = False

        if noti.last_heartbeat >= time.time()-5:
            await asyncio.sleep(10-time.time()+noti.last_heartbeat)

        match service:
            case 'ytnoti':
                parse_name = 'parse_youtube'
            case 'twnoti':
                parse_name = 'parse'

        parser = getattr(noti, parse_name)()
        asyncio.create_task(parser, name=f'{service}:parser')

        await ctx.send(f"{service} successful restart!")

    @commands.command()
    async def disable_autmod(self, ctx: commands.Context):
        spam.RUNNING = False
        await ctx.send(f'{Emoji.success} I have disabled automod!')

    @commands.command()
    async def update_localization(self, ctx: commands.Context):
        self.bot.load_i18n_config()

    @commands.command()
    async def clear_rewards(self, ctx: commands.Context, member: Optional[nextcord.Member] = None):
        if member is None:
            member = ctx.author

        emdb = EconomyMemberDB(member.guild.id, member.id)
        await emdb.update_dict(daily=0, weekly=0, monthly=0)


def setup(bot):
    bot.add_cog(Teams(bot))
