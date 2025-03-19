from asyncio import iscoroutinefunction
import inspect
import logging
import nextcord
from nextcord.ext import commands

from bot.misc.time_transformer import display_time
from bot.databases import GuildDateBases
from bot.languages import i18n
from bot.languages.help import CommandOption, get_command

from typing import Any, Callable, Coroutine, List, TypeVar, Union, get_args, get_origin

from bot.resources.info import DISCORD_SUPPORT_SERVER

_log = logging.getLogger(__name__)
ExceptionT = TypeVar("ExceptionT", bound=BaseException)


class DisabledCommand(commands.CheckFailure):
    pass


class OnlyTeamError(commands.CheckFailure):
    def __init__(self, author: Union[nextcord.Member, nextcord.User]) -> None:
        self.author: Union[nextcord.Member, nextcord.User] = author
        super().__init__()


class InactiveEconomy(commands.CheckFailure):
    pass


class MissingRole(commands.CheckFailure):
    pass


class MissingChannel(commands.CheckFailure):
    pass


class AuthorizationError(commands.CheckFailure):
    pass


def attach_exception(*errors: type[ExceptionT]
                     ) -> Callable[['CallbackCommandError', ExceptionT],
                                   Coroutine[Any, Any, None]]:
    def inner(func):
        nonlocal errors

        if len(errors) == 0:
            sign = inspect.signature(func)
            if isinstance(func, staticmethod):
                params = list(sign.parameters.values())
            else:
                params = list(sign.parameters.values())[1:]
            error = params[0].annotation
            if get_origin(error) is Union:
                errors = get_args(error)
            else:
                errors = (error, )

        func.__attachment_errors__ = errors
        return func
    return inner


class CommandOnCooldown(commands.CommandError):
    def __init__(self, retry_after: float) -> None:
        self.retry_after: float = retry_after
        super().__init__("Cooldown")


def wrap_queue(cls: 'CallbackCommandError'):
    cls.queue = [item for _, item in cls.__dict__.items()
                 if getattr(item, "__attachment_errors__", None) and iscoroutinefunction(item)]
    return cls


@wrap_queue
class CallbackCommandError:
    queue: List[Callable[['CallbackCommandError', Exception],
                         Coroutine[Any, Any, None]]]

    def __init__(self, ctx: commands.Context) -> None:
        self.ctx = ctx
        self.gdb = GuildDateBases(ctx.guild.id)
        self.locale = self.gdb.get_cache('language', 'en')

    @classmethod
    async def process(cls, ctx: commands.Context, error):
        self = cls(ctx)
        self.locale = await self.gdb.get('language')

        for item in self.queue:
            allow_errors = getattr(item, "__attachment_errors__")
            if isinstance(error, allow_errors):
                await item(self, error)
                break
        else:
            await self.parse_ofter_error(error)

    @attach_exception(commands.MissingPermissions)
    async def parse_missing_permissions(self, error):
        content = i18n.t(self.locale, 'errors.MissingPermissions')

        await self.ctx.send(content)

    @attach_exception(commands.BotMissingPermissions)
    async def parse_bot_missing_permissions(self, error):

        content = i18n.t(self.locale, 'errors.BotMissingPermissions')

        await self.ctx.send(content)

    @attach_exception(MissingRole)
    async def parse_missing_role(self, error):
        content = i18n.t(self.locale, 'errors.MissingRole')

        await self.ctx.send(content)

    @attach_exception(MissingChannel)
    async def parse_missing_channel(self, error):
        content = i18n.t(self.locale, 'errors.MissingChannel')

        await self.ctx.send(content)

    @attach_exception(commands.CommandNotFound)
    async def parse_command_not_found(self, error):
        pass

    @attach_exception(commands.NotOwner)
    async def parse_not_owner(self, error):
        content = i18n.t(self.locale, 'errors.NotOwner')

        await self.ctx.send(content=content)

    @attach_exception(OnlyTeamError)
    async def parse_only_team_error(self, error):
        content = i18n.t(self.locale, 'errors.OnlyTeamError')

        await self.ctx.send(content)

    @attach_exception()
    async def parse_bad_argument(self, error: commands.BadArgument):
        title = i18n.t(self.locale, 'errors.BadArgument')
        color = await self.gdb.get('color')

        cmd_data = get_command(self.ctx.command.qualified_name)

        if cmd_data is None:
            return

        using = f"`{cmd_data.get('name')}{' '+' '.join(CommandOption.get_arguments(cmd_data ,self.locale)) if cmd_data.get('arguments') else ''}`"

        embed = nextcord.Embed(
            title=title,
            description=i18n.t(
                self.locale, "help.command-embed.using_command", using=using),
            color=color
        )
        embed.set_footer(text=i18n.t(
            self.locale, "help.arguments"))

        if examples := cmd_data.get('examples'):
            for num, (excmd, descript) in enumerate(examples, start=1):
                embed.add_field(
                    name=i18n.t(
                        self.locale, 'help.command-embed.example', number=num),
                    value=f"`{excmd}`\n{descript.get(self.locale)}",
                    inline=False
                )

        await self.ctx.send(embed=embed)

    @attach_exception()
    async def parse_missing_required_argument(self, error: commands.MissingRequiredArgument):
        param = error.param
        annot = self.ctx.command.callback.__annotations__
        index = list(annot.keys())[1:].index(param.name)

        title = i18n.t(self.locale, 'errors.MissingRequiredArgument')
        color = await self.gdb.get('color')

        cmd_data = get_command(self.ctx.command.name)

        if cmd_data is None:
            return

        using = (
            f"`{cmd_data.get('name')}"
            f"{' '+' '.join(CommandOption.get_arguments(cmd_data, self.locale)) if cmd_data.get('arguments') else ''}`"
        )

        embed = nextcord.Embed(
            title=title,
            description=i18n.t(
                self.locale, "help.command-embed.using_command", using=using),
            color=color
        )
        embed.set_footer(text=i18n.t(
            self.locale, "help.arguments"))

        if examples := cmd_data.get('examples'):
            for num, (excmd, descript) in enumerate(examples, start=1):
                embed.add_field(
                    name=i18n.t(
                        self.locale, 'help.command-embed.example', number=num),
                    value=f"`{excmd}`\n{descript.get(self.locale)}",
                    inline=False
                )

        await self.ctx.send(embed=embed)

    @attach_exception(CommandOnCooldown)
    async def parse_command_on_cooldown(self, error: CommandOnCooldown):
        color = await self.gdb.get('color')

        embed = nextcord.Embed(
            title=i18n.t(self.locale, 'errors.CommandOnCooldown.title'),
            description=i18n.t(self.locale, 'errors.CommandOnCooldown.description',
                               delay=display_time(error.retry_after,
                                                  self.locale)),
            color=color
        )

        await self.ctx.send(embed=embed, delete_after=5.0)

    @attach_exception(InactiveEconomy)
    async def parse_inactive_economy(self, error: InactiveEconomy):
        content = i18n.t(self.locale, 'errors.InactiveEconomy')

        await self.ctx.send(content)

    @attach_exception(DisabledCommand, commands.DisabledCommand)
    async def parse_disabled_command(self, error):
        content = i18n.t(self.locale, 'errors.DisabledCommand')

        await self.ctx.send(content)

    @attach_exception(AuthorizationError)
    async def parse_auth_error(self, error):
        pass

    @attach_exception(commands.CheckFailure)
    async def parse_check_failure(self, error):
        _log.trace("Verification conditions are not met",
                   exc_info=error)

    async def parse_ofter_error(self, error):
        _log.error(
            "Ignoring exception in command %s", self.ctx.command, exc_info=error)

        await self.ctx.author.send(
            i18n.t(self.locale, 'interaction.error.command',
                   DISCORD_SUPPORT_SERVER=DISCORD_SUPPORT_SERVER),
            flags=nextcord.MessageFlags(
                suppress_embeds=True, suppress_notifications=True)
        )
