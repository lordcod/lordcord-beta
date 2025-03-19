import logging
import nextcord
from nextcord.ext import commands, application_checks

from bot.resources.ether import Emoji
from bot.misc import utils
from bot.views.giveaway import GiveawaySettingsView
from bot.misc.lordbot import LordBot
from bot.databases import GuildDateBases
from bot.resources import info
from bot.views.tic_tac_toe import TicTacToe
from bot.views.translate import TranslateView
from bot.languages import i18n
from bot.languages import data as lang_data

import jmespath
import timeit
import googletrans
import asyncio
import random
from typing import Callable, Optional

translator = googletrans.Translator()

_log = logging.getLogger(__name__)


class Basic(commands.Cog):
    def __init__(self, bot: LordBot):
        self.bot = bot

    @commands.command()
    async def ping(self, ctx: commands.Context):
        gdb = GuildDateBases(ctx.guild.id)
        locale = await gdb.get('language')

        stime = timeit.default_timer()
        color = await gdb.get('color')
        ftime = timeit.default_timer()

        discord_latency_ms = round(self.bot.latency*100, 2)
        databases_latency_ms = round((ftime-stime)*100, 2)
        command_latency_ms = round(
            (discord_latency_ms*2)+(databases_latency_ms*10), 2)

        shard_id = (ctx.guild.id >> 22) % self.bot.shard_count

        embed = nextcord.Embed(
            title="Pong!🏓🎉",
            description=i18n.t(locale, 'basic.ping.description',
                               discord_latency_ms=discord_latency_ms,
                               databases_latency_ms=databases_latency_ms,
                               command_latency_ms=command_latency_ms,
                               shard_id=shard_id),
            color=color
        )
        await ctx.send(embed=embed)

    @commands.command()
    @commands.has_permissions(manage_guild=True)
    async def giveaway(self, ctx: commands.Context):
        view = await GiveawaySettingsView(ctx.author, ctx.guild.id)
        await ctx.send(embed=view.embed, view=view)

    @commands.command()
    async def avatar(self, ctx: commands.Context, member: nextcord.Member) -> None:
        gdb = GuildDateBases(ctx.guild.id)
        locale = await gdb.get('language')

        embed = nextcord.Embed(
            title=i18n.t(locale, 'basic.avatar.description', member=member.display_name))
        embed.set_image(member.display_avatar.url)

        await ctx.send(embed=embed)

    @commands.command()
    async def invite(self, ctx: commands.Context):
        gdb = GuildDateBases(ctx.guild.id)
        locale = await gdb.get('language')

        invite_link = f"https://discord.com/oauth2/authorize?client_id={self.bot.user.id}"
        await ctx.send(i18n.t(locale, 'basic.invite.description', invite_link=invite_link))

    @commands.command()
    async def captcha(self, ctx: commands.Context):
        gdb = GuildDateBases(ctx.guild.id)
        lang = await gdb.get('language')
        data, code = await utils.generator_captcha(random.randint(3, 7))
        image_file = nextcord.File(
            data, filename="captcha.png", description="Captcha", spoiler=True)
        await ctx.send(content=i18n.t(lang, 'captcha.enter'), file=image_file)
        check: Callable[
            [nextcord.Message],
            bool] = lambda mes: (mes.channel == ctx.channel
                                 and mes.author == ctx.author)
        try:
            message: nextcord.Message = await self.bot.wait_for("message",
                                                                timeout=30,
                                                                check=check)
        except asyncio.TimeoutError:
            await ctx.send(content=i18n.t(lang, 'captcha.failed'))
            return

        if message.content.upper() == code:
            await ctx.send((f"{Emoji.congratulation}"
                            f"{i18n.t(lang, 'captcha.congratulation')}"))
        else:
            await ctx.send(content=i18n.t(lang, 'captcha.failed'))

    @nextcord.slash_command(
        name="activiti",
        description="Create an activity",
    )
    @application_checks.guild_only()
    async def activiti(
        self,
        interaction: nextcord.Interaction,
        voice: nextcord.VoiceChannel = nextcord.SlashOption(
            required=True,
            name="voice",
            description=("Select the voice channel in which"
                         " the activity will work!")
        ),
        act: str = nextcord.SlashOption(
            required=True,
            name="activiti",
            description="Select the activity you want to use!",
            choices=[activ.get('label') for activ in info.activities_list],
        ),
    ) -> None:
        gdb = GuildDateBases(interaction.guild_id)
        lang = await gdb.get('language')
        color = await gdb.get('color')

        activiti: dict = jmespath.search(
            f"[?label=='{act}']|[0]", info.activities_list)

        try:
            inv = await voice.create_invite(
                target_type=nextcord.InviteTarget.embedded_application,
                target_application_id=activiti.get('id')
            )
        except nextcord.HTTPException:
            await interaction.response.send_message(
                content=i18n.t(lang, 'activiti.failed'))
            return

        view = nextcord.ui.View(timeout=None)
        view.add_item(nextcord.ui.Button(
            label="Activiti", emoji=Emoji.rocket, url=inv.url))

        embed = nextcord.Embed(
            title=i18n.t(lang, 'activiti.embed.title'),
            color=color,
            description=i18n.t(lang, 'activiti.embed.description')
        )
        embed.add_field(
            name=i18n.t(lang, 'activiti.fields.label'),
            value=activiti.get('label')
        )
        embed.add_field(
            name=i18n.t(lang, 'activiti.fields.max-user'),
            value=activiti.get('max_user')
        )

        await interaction.response.send_message(embed=embed,
                                                view=view)

    @nextcord.message_command(name="Translate")
    async def translate(
        self,
        inters: nextcord.Interaction,
        message: nextcord.Message
    ):
        gdb = GuildDateBases(inters.guild_id)
        locale = await gdb.get('language')

        if not message.content:
            await inters.response.send_message(i18n.t(locale, 'translate.failed'),
                                               ephemeral=True)
            return

        data = jmespath.search(
            f"[?discord_language=='{inters.locale}']|[0]", lang_data)

        result = translator.translate(
            text=message.content, dest=data.get('google_language'))

        view = await TranslateView(inters.guild_id, data.get('google_language'))

        await inters.response.send_message(content=result.text,
                                           view=view,
                                           ephemeral=True)

    @commands.command()
    async def tic(self, ctx: commands.Context, member: Optional[nextcord.Member] = None):
        await ctx.send("Tic Tac Toe: X goes first", view=TicTacToe(ctx.author, member))


def setup(bot):
    bot.add_cog(Basic(bot))
