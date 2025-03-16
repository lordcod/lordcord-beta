import math
import re
from typing import Iterable
import nextcord
from nextcord.ext import commands

from bot.languages import help as help_info, i18n
from bot.languages.help import get_command
from bot.databases import GuildDateBases
from bot.misc.lordbot import LordBot
from bot.misc.utils import get_emoji_wrap
from bot.views.help import HelpView


REGEXP_COMMAND_NAME = re.compile(r'([ _\-\.a-zA-Z0-9]+)')


def get_disable_command_value(
    locale: str,
    command: help_info.CommandOption
) -> str:
    return i18n.t(locale,
                  f"help.command-embed.connection_disabled.{int(command.get('allowed_disabled'))}")


def get_using(
    locale: str,
    command: help_info.CommandOption
) -> str:
    arguments = [i18n.t(locale, f"commands.command.{command.get('name')}.arguments.{i}")
                 for i in range(command.get('count_args'))]
    return i18n.t(locale, 'help.command-embed.using_command',
                  using=f"{command.get('name')}{' '+' '.join(arguments) if arguments else ''}")


def divise_list(iterable: Iterable, count: int) -> list:
    iterable = list(iterable)
    ret = []
    score = math.ceil(len(iterable)/count)
    for i in range(count):
        ret.append(iterable[score*i:score*(i+1)])
    return ret


class Help(commands.Cog):
    def __init__(self, bot: LordBot):
        self.bot = bot

    @commands.command()
    async def help(self, ctx: commands.Context, *, command_name: str = None):
        if not command_name:
            await self.send_message(ctx)
            return

        if not REGEXP_COMMAND_NAME.fullmatch(command_name):
            await self.send_not_found(ctx)
            return

        command_data = get_command(command_name)
        if command_data:
            await self.send_command(ctx, command_data)
            return

        await self.send_not_found(ctx)

    async def send_message(self, ctx: commands.Context):
        gdb = GuildDateBases(ctx.guild.id)

        locale = await gdb.get('language')
        color = await gdb.get('color')
        get_emoji = await get_emoji_wrap(gdb)

        embed = nextcord.Embed(
            title=i18n.t(locale, "help.title"),
            color=color
        )

        for category, coms in help_info.categories.items():
            text = ''
            for cmd in coms:
                text += f"`{cmd.get('name')}` "

            category_emoji = get_emoji(help_info.categories_emoji.get(category))
            category_name = i18n.t(locale, f'commands.category.{category}')
            embed.add_field(
                name=f'{category_emoji} {category_name}',
                value=text,
                inline=False
            )

        view = await HelpView(ctx.guild.id)

        await ctx.send(embed=embed, view=view)

    async def send_command(self, ctx: commands.Context, command_data: help_info.CommandOption):
        gdb = GuildDateBases(ctx.guild.id)

        locale = await gdb.get('language')
        color = await gdb.get('color')
        get_emoji = await get_emoji_wrap(gdb)
        aliases = command_data.get('aliases')
        category_emoji = get_emoji(help_info.categories_emoji.get(command_data.get('category')))
        category_name = i18n.t(locale, f"commands.category.{command_data.get('category')}")

        embed = nextcord.Embed(
            title=i18n.t(locale, "help.command-embed.title",
                         name=command_data.get('name')),
            description=i18n.t(locale, f"commands.command.{command_data.get('name')}.description"),
            color=color
        )
        embed.set_footer(
            text=i18n.t(locale, "help.arguments")
        )
        embed.add_field(
            name=i18n.t(
                locale, 'help.command-embed.info'),
            value=(
                f"{i18n.t(locale, 'help.command-embed.category', category_emoji=category_emoji, category_name=category_name)}"
                f"{i18n.t(locale, 'help.command-embed.aliases', aliases=', '.join([f'`{al}`' for al in aliases])) if aliases else ''}"
                f"{get_using(locale, command_data)}"
                f"{i18n.t(locale, 'help.command-embed.disable_command', value=get_disable_command_value(locale, command_data))}"
            ),
            inline=False
        )
        for i in range(command_data.get('count_examples')):
            using = i18n.t(locale, f"commands.command.{command_data.get('name')}.examples.{i}.use")
            description = i18n.t(locale, f"commands.command.{command_data.get('name')}.examples.{i}.desc")
            embed.add_field(
                name=i18n.t(
                    locale, 'help.command-embed.example', number=i+1),
                value=f"`{using}`\n{description}",
                inline=False
            )

        await ctx.send(embed=embed)

    async def send_not_found(self, ctx: commands.Context):
        gdb = GuildDateBases(ctx.guild.id)

        locale = await gdb.get('language')
        color = await gdb.get('color')

        embed = nextcord.Embed(
            title=i18n.t(locale, "help.command-notfound.title"),
            description=i18n.t(locale, "help.command-notfound.description"),
            color=color
        )

        await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Help(bot))
