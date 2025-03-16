import contextlib
import logging
import sys
import traceback
import nextcord
from nextcord.ext import commands
from bot.databases.handlers.guildHD import GuildDateBases
from bot.languages import i18n
from bot.misc.lordbot import LordBot

from bot.misc.ratelimit import Cooldown
from bot.resources import errors
from bot.databases import CommandDB
from bot.resources.errors import (AuthorizationError, CallbackCommandError,
                                  MissingRole,
                                  MissingChannel,
                                  CommandOnCooldown)
from bot.resources.ether import Emoji
from bot.resources.info import DISCORD_SUPPORT_SERVER

_log = logging.getLogger(__name__)


class PermissionChecker:
    def __init__(self, ctx: commands.Context) -> None:
        self.ctx = ctx

    async def process(self) -> bool:
        ctx = self.ctx
        command_name = ctx.command.qualified_name
        cdb = CommandDB(ctx.guild.id)
        self.command_permissions = await cdb.get(command_name, {})

        enabled = await self.is_enabled()
        allowed = await self.is_allowed()

        answer = enabled & allowed
        return answer

    async def is_enabled(self):
        "Checks whether it is enabled"
        command_permissions = self.command_permissions
        operate = command_permissions.get("operate", 1)

        if operate == 0:
            raise errors.DisabledCommand()
        return True

    async def is_allowed(self):
        "Checks if there are permissions to use the command"
        command_permissions = self.command_permissions
        distribution: dict = command_permissions.get("distribution", {})

        for type, data in distribution.items():
            meaning = self.allowed_types[type]
            value = await meaning(self, data)
            if not value:
                return False
        return True

    async def _is_allowed_role(self, data: dict) -> bool:
        "The `is_allowed` subsection is needed to verify roles"
        ctx = self.ctx
        author = ctx.author
        aut_roles_ids = author._roles

        if not data:
            return True

        common = set(data) & set(aut_roles_ids)
        if not common:
            raise MissingRole()
        return True

    async def _is_allowed_channel(self, data: dict) -> bool:
        "The `is_allowed` subsection is needed to verify channels"
        ctx = self.ctx
        channel = ctx.channel
        channels_ids = data.get("channels", [])
        categories_ids = data.get("categories", [])

        if not (channel.id in channels_ids or
                channel.category_id in categories_ids):
            raise MissingChannel()
        return True

    async def _is_denyed_role(self, data: dict) -> bool:
        "The `is_allowed` subsection is needed to verify roles"
        ctx = self.ctx
        author = ctx.author
        aut_roles_ids = author._roles

        if not data:
            return True

        common = set(data) & set(aut_roles_ids)
        if common:
            raise MissingRole()
        return True

    async def _is_denyed_channel(self, data: dict) -> bool:
        "The `is_allowed` subsection is needed to verify channels"
        ctx = self.ctx
        channel = ctx.channel
        channels_ids = data.get("channels", [])
        categories_ids = data.get("categories", [])

        if (channel.id in channels_ids or
                channel.category_id in categories_ids):
            raise MissingChannel()
        return True

    async def _is_cooldown(self, data: dict) -> bool:
        ctx = self.ctx

        cooldown = Cooldown.from_message(
            ctx.command.qualified_name,
            data,
            ctx.message
        )
        ctx.cooldown = cooldown
        retry = cooldown.get()

        if retry is None:
            return True
        elif isinstance(retry, float):
            raise CommandOnCooldown(retry)
        else:
            raise TypeError(retry)

    allowed_types = {
        'allow-role': _is_allowed_role,
        'allow-channel': _is_allowed_channel,
        'deny-channel': _is_denyed_channel,
        'deny-role': _is_denyed_role,
        'cooldown': _is_cooldown
    }


class CommandEvent(commands.Cog):
    def __init__(self, bot: LordBot) -> None:
        self.bot = bot

        super().__init__()

        bot.after_invoke(self.after_invoke)
        bot.set_event(self.on_error)
        bot.set_event(self.on_command_error)
        bot.set_event(self.on_application_command_error)
        bot.set_event(self.on_application_item_error)

        bot.add_check(self.permission_check)

    async def on_application_item_error(
        self,
        exception: Exception,
        item: nextcord.ui.Item,
        interaction: nextcord.Interaction,
    ) -> None:
        if not (interaction.is_expired() or interaction.response.is_done()):
            gdb = GuildDateBases(interaction.guild_id)
            locale = await gdb.get('language')
            custom_id = (item.custom_id if item._provided_custom_id
                         else item.custom_id[:8])
            with contextlib.suppress(nextcord.HTTPException):
                await interaction.response.send_message(
                    i18n.t(locale, 'interaction.error.item',
                           custom_id=custom_id, DISCORD_SUPPORT_SERVER=DISCORD_SUPPORT_SERVER),
                    ephemeral=True,
                    flags=nextcord.MessageFlags(suppress_embeds=True)
                )

        _log.error("Ignoring exception in item %s with custom id %s:",
                   item, item.custom_id, exc_info=exception)

    async def on_application_command_error(
        self,
        interaction: nextcord.Interaction,
        exception: nextcord.ApplicationError
    ) -> None:
        if interaction.application_command is None:
            return  # Not supposed to ever happen

        if interaction.application_command.has_error_handler():
            return

        cog = interaction.application_command.parent_cog
        if cog and cog.has_application_command_error_handler():
            return

        if not (interaction.is_expired() or interaction.response.is_done()):
            gdb = GuildDateBases(interaction.guild_id)
            locale = await gdb.get('language')
            with contextlib.suppress(nextcord.NotFound):
                await interaction.response.send_message(
                    i18n.t(locale, 'interaction.error.command',
                           DISCORD_SUPPORT_SERVER=DISCORD_SUPPORT_SERVER),
                    ephemeral=True,
                    flags=nextcord.MessageFlags(suppress_embeds=True)
                )

        _log.error("Ignoring exception in command %s:",
                   interaction.application_command, exc_info=exception)

    async def on_command_error(self, ctx: commands.Context, error: Exception):
        if self.bot.release_bot:
            await CallbackCommandError.process(ctx, error)
            return

        emoji_url = nextcord.PartialEmoji.from_str(Emoji.cross).url
        embed = nextcord.Embed(
            description='```' + '\n'.join(traceback.format_exception(error)) + '```',
            color=nextcord.Colour.brand_red()
        )
        embed.set_author(
            name='Error',
            icon_url=emoji_url
        )
        await ctx.send(embed=embed)

    async def on_error(self, event, *args, **kwargs):
        _log.error(
            "Ignoring exception in event %s", event, exc_info=sys.exc_info())

    async def permission_check(self, ctx: commands.Context):
        if ctx.guild is None or ctx.channel is None:
            return
        permission = ctx.channel.permissions_for(ctx.guild.me)
        if not (permission.read_messages and permission.send_messages and permission.embed_links):
            raise AuthorizationError(
                'Authorization of rights has not been completed')

        perch = PermissionChecker(ctx)
        answer = await perch.process()

        return answer

    async def after_invoke(self, ctx: commands.Context) -> None:
        if cooldown := getattr(ctx, 'cooldown', None):
            cooldown.add()


def setup(bot):
    bot.add_cog(CommandEvent(bot))
