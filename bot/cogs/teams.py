import asyncio
import time
from typing import Literal
import nextcord
from nextcord.ext import commands

from bot.databases import localdb
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
        await self.bot._LordBot__session.close()
        await localdb._update_db(__name__)
        await localdb.cache.close(close_connection_pool=True)

        conn = self.bot.engine._DataBase__connection
        if conn and not conn.closed:
            conn.close()

        await ctx.send("The bot has activated the completion process!")
        await self.bot.close()

    @commands.command(aliases=['sudo'])
    @commands.guild_only()
    async def subo(
        self, ctx: commands.Context, member: nextcord.Member, *, command: str
    ):
        ctx.message.author = member
        await self.bot.process_with_str(ctx.message, command)

    @commands.command(aliases=['load_cog'])
    async def load_extension(self, ctx: commands.Context, name):
        self.bot.load_extension(f"bot.cogs.{name}")
        await ctx.send(f"Service **{name}** successfully enabled")

    @commands.command(aliases=['api_config'])
    async def get_api_config(self, ctx: commands.Context):
        api = self.bot.apisite
        if not api.is_running():
            return

        await ctx.send('ApiSite is worked\n'
                       f'Public url: {api.callback_url}\n'
                       f'Password: {api.password}')

    @commands.command()
    async def update_api_config(self, ctx: commands.Context):
        await self.bot.update_api_config()

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

    @commands.command(aliases=['update_db'])
    async def update_redis(
        self,
        ctx: commands.Context
    ):
        await localdb._update_db(__name__)
        await ctx.message.add_reaction(Emoji.success)

    @commands.command(aliases=['notifi_info'])
    async def get_notifi_info(self, ctx: commands.Context):
        twnoti = self.bot.twnoti
        ytnoti = self.bot.ytnoti

        await ctx.send(
            'Notification is worked\n'
            f'Twitch: {twnoti.running} (<t:{twnoti.last_heartbeat :.0f}:R>)\n'
            f'Youtube: {ytnoti.running} (<t:{ytnoti.last_heartbeat :.0f}:R>)'
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
    async def get_apps(self, ctx: commands.Context, page: int = 0):
        await ctx.send(
            '\n'.join([
                f'{bot.mention} - [reinvite](https://discord.com/oauth2/authorize?client_id={bot.id}&scope=bot+applications.commands)'
                for bot in ctx.guild.bots
            ][page*10:page*10+10]) or '...'
        )


def setup(bot):
    bot.add_cog(Teams(bot))
