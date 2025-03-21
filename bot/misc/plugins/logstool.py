from __future__ import annotations

import asyncio
import contextlib
from dataclasses import dataclass
import datetime
from enum import IntEnum
import functools
import logging
from typing import Any, Callable, Coroutine, Dict, List, Optional,  Tuple, TypeVar
import nextcord

from bot.databases import GuildDateBases, localdb
from bot.misc.time_transformer import display_time
from bot.misc.utils import cut_back

_log = logging.getLogger(__name__)
LT = TypeVar('LT')


@dataclass
class Message:
    content: Optional[str] = None
    embed: Optional[nextcord.Embed] = None
    embeds: Optional[List[nextcord.Embed]] = None
    file: Optional[nextcord.File] = None
    files: Optional[List[nextcord.File]] = None

    def keys(self) -> List[str]:
        return [k for k, v in self.__dict__.items() if v is not None]

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key, None)


class LogType(IntEnum):
    # TODO: Create log: tempvoice
    delete_message = 0
    edit_message = 1
    punishment = 2
    economy = 3
    ideas = 4
    voice_state = 5
    tickets = 6
    # tempvoice = 7
    roles = 8


def embed_to_text(embed: nextcord.Embed) -> str:
    return '\n'.join([
        cut_back(embed.title, 200),
        cut_back(embed.author.name, 100),
        cut_back(embed.description, 1000),
        cut_back(embed.footer.text, 200)
    ])


def filter_bool(texts: list) -> list:
    return list(filter(
        lambda item: item,
        texts
    ))


_message_log: Dict[Tuple[int, int], asyncio.Future] = {}


async def pre_message_delete_log(message: nextcord.Message):
    moderator: Optional[nextcord.Member] = None
    loop = asyncio.get_event_loop()
    future = loop.create_future()
    _message_log[(message.channel.id, message.author.id)] = future

    try:
        await asyncio.wait_for(future, timeout=1)
    except asyncio.TimeoutError:
        pass
    else:
        moderator = future.result()
    finally:
        _message_log.pop((message.channel.id, message.author.id), None)

    await Logs(message.guild).delete_message(message, moderator)


async def set_message_delete_audit_log(moderator: nextcord.Member, channel_id: int, author_id: int) -> None:
    try:
        _message_log[(channel_id, author_id)].set_result(moderator)
    except KeyError:
        pass


_roles_tasks = {}
_roles_db: Dict[str, Tuple[List[nextcord.Role], List[nextcord.Role]]] = {}


def _start_role_task():
    loop = asyncio.get_event_loop()
    future = loop.create_future()
    th = loop.call_later(10, future.set_result, None)

    def wrapped():
        nonlocal th
        th.cancel()
        th = loop.call_later(10, future.set_result, None)
    return future, wrapped


async def _wait_change_role(future: asyncio.Future, member: nextcord.Member):
    with contextlib.suppress(asyncio.TimeoutError):
        await asyncio.wait_for(future, timeout=60)
    key = f'{member.guild.id}:{member.id}'

    _added, _removed = map(set, _roles_db[key])
    _missing = _added & _removed
    added, removed = map(lambda roles: [role for role in roles
                                        if member.guild.get_role(role.id)],
                         (_added-_missing, _removed-_missing))
    if added or removed:
        await Logs(member.guild).change_role(member, added, removed)

    del _roles_tasks[key]
    del _roles_db[key]


async def pre_add_role(member: nextcord.Member, role: nextcord.Role) -> None:
    key = f'{member.guild.id}:{member.id}'
    task = _roles_tasks.get(key)
    if task is None:
        future, up = _start_role_task()
        _roles_tasks[key] = up
        _roles_db[key] = ([], [])
        asyncio.create_task(_wait_change_role(future, member))
    else:
        task()
    _roles_db[key][0].append(role)


async def pre_remove_role(member: nextcord.Member, role: nextcord.Role) -> None:
    key = f'{member.guild.id}:{member.id}'
    task = _roles_tasks.get(key)
    if task is None:
        future, up = _start_role_task()
        _roles_tasks[key] = up
        _roles_db[key] = ([], [])
        asyncio.create_task(_wait_change_role(future, member))
    else:
        task()
    _roles_db[key][1].append(role)


async def get_webhook(channel: nextcord.TextChannel) -> Optional[nextcord.Webhook]:
    client = channel._state._get_client()
    webhooks_db = await localdb.get_table('logs_webhooks')
    webhook_data = await webhooks_db.get(channel.id)
    _log.trace(webhook_data)

    if webhook_data is not None:
        webhook_data['type'] = 1
        cache_webhook = nextcord.Webhook.from_state(webhook_data, channel._state)
        _log.trace(cache_webhook)

        with contextlib.suppress(nextcord.NotFound):
            webhook = await cache_webhook.fetch(prefer_auth=False)
            _log.trace(webhook)
            if webhook.channel_id == channel.id:
                return webhook

    if not channel.permissions_for(channel.guild.me).manage_webhooks:
        return None

    webhook = await channel.create_webhook(
        name=f'{client.user.name} Logs',
        avatar=client.user.avatar
    )
    await webhooks_db.set(channel.id, {'id': webhook.id, 'token': webhook.token})

    return webhook


def on_logs(log_type: int):
    def predicte(coro):
        async def send_log(self: Logs, mes: Message, channel_id: int, logs_types: List[LogType]):
            if log_type not in logs_types:
                return

            channel = self.guild.get_channel(channel_id)
            if channel is None:
                return

            webhook = await get_webhook(channel)
            if webhook is None:
                return

            await webhook.send(**mes)

        @functools.wraps(coro)
        async def wrapped(self: Logs, *args, **kwargs) -> None:
            tasks = []

            if self.guild is None:
                return

            mes: Optional[Message] = await coro(self, *args, **kwargs)
            guild_data: Dict[int, List[LogType]] = await self.gdb.get('logs')

            if mes is None or guild_data is None:
                return

            for channel_id, logs_types in guild_data.items():
                tasks.append(asyncio.create_task(send_log(self, mes, channel_id, logs_types)))

            for task in tasks:
                await task
        return wrapped
    return predicte


class Logs:
    def __init__(self, guild: Optional[nextcord.Guild]):
        if guild is None:
            self.guild = None
            return
        self.guild = guild
        self.gdb = GuildDateBases(guild.id)

    @on_logs(LogType.delete_message)
    async def delete_message(self, message: nextcord.Message, moderator: Optional[nextcord.Member] = None):
        if message.author.bot:
            return

        embed = nextcord.Embed(
            title="Message deleted",
            color=nextcord.Colour.red(),
            description=(
                f"> Channel: {message.channel.name} ({message.channel.mention})\n"
                f"> Message id: {message.id}\n"
                f"> Message author: {str(message.author)} ({message.author.mention})\n"
                f"> Message created: <t:{message.created_at.timestamp() :.0f}:f> (<t:{message.created_at.timestamp() :.0f}:R>)"
            ),
            timestamp=datetime.datetime.today()
        )
        if message.content:
            embed.add_field(
                name="Message",
                value=message.content[:1024]
            )
        if moderator:
            embed.set_footer(text=moderator,
                             icon_url=moderator.display_avatar)
        if message.attachments:
            files = await asyncio.gather(*[
                attach.to_file()
                for attach in message.attachments
            ])
        else:
            files = None
        return Message(embed=embed, files=files)

    @on_logs(LogType.edit_message)
    async def edit_message(self, before: nextcord.Message, after: nextcord.Message):
        if after.author.bot:
            return

        if before.content == after.content:
            editted = {}
            for slot in nextcord.Message.__slots__:
                if getattr(before, slot, None) != getattr(after, slot, None):
                    editted[slot] = (getattr(before, slot, None),
                                     getattr(after, slot, None))
            _log.trace('[%d] Eddited data: %s', after.id, editted)

            if len(before.attachments) > 0 and len(after.attachments) == 0:
                embed = nextcord.Embed(
                    title="Message edited",
                    color=nextcord.Colour.orange(),
                    description=(
                        f"> Channel: {before.channel.name} ({before.channel.mention})\n"
                        f"> Message id: {before.id}\n"
                        f"> Message author: {str(before.author)} ({before.author.mention})\n"
                        f"> Message created: <t:{before.created_at.timestamp() :.0f}:f> (<t:{before.created_at.timestamp() :.0f}:R>)"
                    ),
                    timestamp=datetime.datetime.today()
                )
                embed.add_field(
                    name='Action',
                    value='Remove all attachments'
                )
                return Message(embed=embed)
            return

        embed = nextcord.Embed(
            title="Message edited",
            color=nextcord.Colour.orange(),
            description=(
                f"> Channel: {before.channel.name} ({before.channel.mention})\n"
                f"> Message id: {before.id}\n"
                f"> Message author: {str(before.author)} ({before.author.mention})\n"
                f"> Message created: <t:{before.created_at.timestamp() :.0f}:f> (<t:{before.created_at.timestamp() :.0f}:R>)"
            ),
            timestamp=datetime.datetime.today()
        )
        embed.add_field(
            name="Before",
            value=before.content[:1024]
        )
        embed.add_field(
            name="After",
            value=after.content[:1024]
        )
        return Message(embed=embed)

    @on_logs(LogType.punishment)
    async def timeout(
            self,
            member: nextcord.Member,
            duration: int,
            moderator: nextcord.Member,
            reason: Optional[str] = None):
        embed = nextcord.Embed(
            title='Timeout',
            color=nextcord.Colour.red(),
            description=(
                f'> Member: {member} ({member.id})\n'
                f'> Disabled on: {display_time(duration)}\n'
                f'> Moderator: {moderator} ({moderator.id})\n'
                f"{f'> Reason: {reason}' if reason else ''}"
            ),
            timestamp=datetime.datetime.today()
        )
        embed.set_thumbnail(member.display_avatar)
        return Message(embed=embed)

    @on_logs(LogType.punishment)
    async def untimeout(self,
                        member: nextcord.Member,
                        duration: Optional[int] = None,
                        moderator: Optional[nextcord.Member] = None,
                        reason: Optional[str] = None):
        embed = nextcord.Embed(
            title='Untimeout',
            color=nextcord.Colour.red(),
            description=f"> Member: {member} ({member.id})",
            timestamp=datetime.datetime.today()
        )
        if duration:
            embed.description += f'\n> Spent in the mute: {display_time(duration)}'
        if moderator:
            embed.description += f'\n> Moderator: {moderator} ({moderator.id})'
        if reason:
            embed.description += f'\n> Reason: {reason}'
        embed.set_thumbnail(member.display_avatar)
        return Message(embed=embed)

    @on_logs(LogType.punishment)
    async def kick(self, guild: nextcord.Guild, user: nextcord.User,
                   moderator: nextcord.Member, reason: Optional[str]):
        embed = nextcord.Embed(
            title='Kick',
            color=nextcord.Colour.red(),
            description=(
                f'> Member: {user} ({user.id})\n'
                f'> Moderator: {moderator} ({moderator.id})\n'
                f"{f'> Reason: {reason}' if reason else ''}"
            ),
            timestamp=datetime.datetime.today()
        )
        embed.set_thumbnail(user.display_avatar)
        return Message(embed=embed)

    @on_logs(LogType.punishment)
    async def ban(self, guild: nextcord.Guild, user: nextcord.User,
                  moderator: nextcord.Member, reason: Optional[str]):
        embed = nextcord.Embed(
            title='Ban',
            color=nextcord.Colour.red(),
            description=(
                f'> Member: {user} ({user.id})\n'
                f'> Moderator: {moderator} ({moderator.id})\n'
                f"{f'> Reason: {reason}' if reason else ''}"
            ),
            timestamp=datetime.datetime.today()
        )
        embed.set_thumbnail(user.display_avatar)
        return Message(embed=embed)

    @on_logs(LogType.punishment)
    async def unban(self, guild: nextcord.Guild, user: nextcord.User,
                    moderator: nextcord.Member, reason: Optional[str]):
        embed = nextcord.Embed(
            title='Unbam',
            color=nextcord.Colour.red(),
            description=(
                f'> Member: {user} ({user.id})\n'
                f'> Moderator: {moderator} ({moderator.id})\n'
                f"{f'> Reason: {reason}' if reason else ''}"
            ),
            timestamp=datetime.datetime.today()
        )
        embed.set_thumbnail(user.display_avatar)
        return Message(embed=embed)

    @on_logs(LogType.economy)
    async def add_currency(self, member: nextcord.Member, amount: int, moderator: Optional[nextcord.Member] = None, reason: Optional[str] = None):
        gdb = GuildDateBases(member.guild.id)
        economy_settings = await gdb.get('economic_settings')
        currency_emoji = economy_settings.get('emoji')
        embed = nextcord.Embed(
            title='Currency received',
            color=nextcord.Colour.brand_green(),
            description=(
                f'> Member: **{member.name}** (**{member.id}**)\n'
                f'> Amount: *{amount :,}*{currency_emoji}'
            ),
            timestamp=datetime.datetime.today()
        )
        if moderator:
            embed.description += f'\n> Moderator: **{moderator.name}** (**{moderator.id}**)'
        if reason:
            embed.description += f'\n> Reason: {reason}'
        embed.set_thumbnail(member.display_avatar)
        return Message(embed=embed)

    @on_logs(LogType.economy)
    async def add_currency_for_ids(self, role: nextcord.Role, amount: int, moderator: Optional[nextcord.Member] = None, reason: Optional[str] = None):
        gdb = GuildDateBases(role.guild.id)
        economy_settings = await gdb.get('economic_settings')
        currency_emoji = economy_settings.get('emoji')
        embed = nextcord.Embed(
            title='Currency received',
            color=nextcord.Colour.brand_green(),
            description=(
                f'> Role: {role.mention} (**{role.id}**)\n'
                f'> Amount: *{amount :,}*{currency_emoji}'
            ),
            timestamp=datetime.datetime.today()
        )
        if moderator:
            embed.description += f'\n> Moderator: **{moderator.name}** (**{moderator.id}**)'
        if reason:
            embed.description += f'\n> Reason: {reason}'
        embed.set_thumbnail(role.icon)
        return Message(embed=embed)

    @on_logs(LogType.economy)
    async def remove_currency(self, member: nextcord.Member, amount: int, moderator: Optional[nextcord.Member] = None, reason: Optional[str] = None):
        gdb = GuildDateBases(member.guild.id)
        economy_settings = await gdb.get('economic_settings')
        currency_emoji = economy_settings.get('emoji')
        embed = nextcord.Embed(
            title='Currency was taken',
            color=nextcord.Colour.red(),
            description=(
                f'> Member: **{member.name}** (**{member.id}**)\n'
                f'> Amount: *{amount :,}*{currency_emoji}'
            ),
            timestamp=datetime.datetime.today()
        )
        if moderator:
            embed.description += f'\n> Moderator: **{moderator.name}** (**{moderator.id}**)'
        if reason:
            embed.description += f'\n> Reason: {reason}'
        embed.set_thumbnail(member.display_avatar)
        return Message(embed=embed)

    @on_logs(LogType.ideas)
    async def create_idea(self, member: nextcord.Member, idea: str, image: Optional[str] = None):
        embed = nextcord.Embed(
            title='Created new idea',
            description=(
                f'> Member: **{member.name}** (**{member.id}**)\n'
                f'>>> Idea: {idea}'
            ),
            color=nextcord.Colour.orange(),
            timestamp=datetime.datetime.today()
        )
        embed.set_thumbnail(member.display_avatar)
        embed.set_image(image)
        return Message(embed=embed)

    @on_logs(LogType.ideas)
    async def approve_idea(self, moderator: nextcord.Member, member: nextcord.Member, idea: str, image: Optional[str] = None, reason: Optional[str] = None):
        embed = nextcord.Embed(
            title='Approved idea',
            description=(
                f'> Member: **{member.name}** (**{member.id}**)\n'
                f'> Moderator: **{moderator.name}** (**{moderator.id}**)\n'
                f'>>> Idea: {idea}'
            ),
            color=nextcord.Colour.brand_green(),
            timestamp=datetime.datetime.today()
        )
        if reason:
            embed.description += f'\nReason: {reason}'
        embed.set_thumbnail(member.display_avatar)
        if image:
            embed.set_image(image)
        embed.set_footer(text=str(moderator.name),
                         icon_url=moderator.display_avatar)
        return Message(embed=embed)

    @on_logs(LogType.ideas)
    async def deny_idea(self, moderator: nextcord.Member, member: nextcord.Member, idea: str, image: Optional[str] = None, reason: Optional[str] = None):
        embed = nextcord.Embed(
            title='Denied idea',
            description=(
                f'> Member: **{member.name}** (**{member.id}**)\n'
                f'> Moderator: **{moderator.name}** (**{moderator.id}**)'
                f'>>> Idea: {idea}'
            ),
            color=nextcord.Colour.red(),
            timestamp=datetime.datetime.today()
        )
        if reason:
            embed.description += f'\nReason: {reason}'
        embed.set_thumbnail(member.display_avatar)
        if image:
            embed.set_image(image)
        embed.set_footer(text=str(moderator.name),
                         icon_url=moderator.display_avatar)
        return Message(embed=embed)

    @on_logs(LogType.roles)
    async def change_role(self, member: nextcord.Member, added: List[nextcord.Role], removed: List[nextcord.Role]):
        embed = nextcord.Embed(
            title='Сhanging roles',
            description=(
                f'> Member: **{member.name} ({member.id})**'
            ),
            color=nextcord.Colour.orange(),
            timestamp=datetime.datetime.today()
        )
        embed.set_thumbnail(member.display_avatar)
        if added:
            embed.add_field(
                name='Added roles',
                value=', '.join([role.mention for role in added])
            )
        if removed:
            embed.add_field(
                name='Removed roles',
                value=', '.join([role.mention for role in removed])
            )
        return Message(embed=embed)

    @on_logs(LogType.voice_state)
    async def connect_voice(self, member: nextcord.Member, channel: nextcord.VoiceChannel):
        embed = nextcord.Embed(
            title='Connecting to voice',
            description=(
                f'> Member: **{member.name}** (**{member.id}**)\n'
                f'> Channel: {channel.mention} (**{channel.id}**)'
            ),
            color=nextcord.Colour.brand_green(),
            timestamp=datetime.datetime.today()
        )
        embed.set_thumbnail(member.display_avatar)
        return Message(embed=embed)

    @on_logs(LogType.voice_state)
    async def disconnect_voice(self, member: nextcord.Member, channel: nextcord.VoiceChannel):
        embed = nextcord.Embed(
            title='Disconnecting to voice',
            description=(
                f'> Member: **{member.name}** (**{member.id}**)\n'
                f'> Channel: {channel.mention} (**{channel.id}**)'
            ),
            color=nextcord.Colour.brand_red(),
            timestamp=datetime.datetime.today()
        )
        embed.set_thumbnail(member.display_avatar)
        return Message(embed=embed)

    @on_logs(LogType.voice_state)
    async def move_voice(self, member: nextcord.Member, before: nextcord.VoiceChannel, after: nextcord.VoiceChannel):
        embed = nextcord.Embed(
            title='Moving to voice',
            description=(
                f'> Member: **{member.name}** (**{member.id}**)\n'
                f'> Old channel: {before.mention} (**{before.id}**)\n'
                f'> New channel: {after.mention} (**{after.id}**)'
            ),
            color=nextcord.Colour.orange(),
            timestamp=datetime.datetime.today()
        )
        embed.set_thumbnail(member.display_avatar)
        return Message(embed=embed)

    @on_logs(LogType.tickets)
    async def create_ticket(
        self,
        member: nextcord.Member,
        panel_channel_id: int,
        channel: nextcord.TextChannel,
        inputs: Optional[dict[str, str]],
        category_name: Optional[str],
        ticket_count: Optional[dict[str, int]]
    ):
        panel_channel = self.guild.get_channel(panel_channel_id)

        embeds = []
        embed = nextcord.Embed(
            title='Create ticket',
            description=(
                f'> Member: **{member.name}** (**{member.id}**)\n'
                f'> Panel channel: {panel_channel.mention} (**{panel_channel.id}**)\n'
                f'> Channel: {channel.mention} (**{channel.id}**)'
            ),
            color=nextcord.Colour.orange(),
            timestamp=datetime.datetime.today()
        )
        if category_name:
            embed.description += f'\n> Category: {category_name}'
        if ticket_count:
            embed.description += f"\n> Active ticket count: {ticket_count['active']}"
            embed.description += f"\n> Total ticket count: {ticket_count['total']}"

        embeds.append(embed)

        if inputs:
            input_embed = nextcord.Embed(
                color=nextcord.Colour.orange(),
                description='\n'.join(
                    f"**{label}**```\n{res}```"
                    for label, res in inputs.items()
                ),
                timestamp=datetime.datetime.today()
            )
            embeds.append(input_embed)

        embed.set_thumbnail(member.display_avatar)
        return Message(embed=embed)

    @on_logs(LogType.tickets)
    async def close_ticket(
        self,
        owner: nextcord.Member,
        member: nextcord.Member,
        panel_channel_id: int,
        channel: nextcord.TextChannel
    ):
        panel_channel = self.guild.get_channel(panel_channel_id)

        embeds = []
        embed = nextcord.Embed(
            title='Close ticket',
            description=(
                f'> Owner: **{owner.name}** (**{owner.id}**)\n'
                f'> Member: **{member.name}** (**{member.id}**)\n'
                f'> Panel channel: {panel_channel.mention} (**{panel_channel.id}**)\n'
                f'> Channel: {channel.mention} (**{channel.id}**)'
            ),
            color=nextcord.Colour.brand_red(),
            timestamp=datetime.datetime.today()
        )

        embeds.append(embed)
        embed.set_thumbnail(member.display_avatar)
        return Message(embed=embed)

    @on_logs(LogType.tickets)
    async def reopen_ticket(
        self,
        owner: nextcord.Member,
        member: nextcord.Member,
        panel_channel_id: int,
        channel: nextcord.TextChannel
    ):
        panel_channel = self.guild.get_channel(panel_channel_id)

        embeds = []
        embed = nextcord.Embed(
            title='Reopen ticket',
            description=(
                f'> Owner: **{owner.name}** (**{owner.id}**)\n'
                f'> Member: **{member.name}** (**{member.id}**)\n'
                f'> Panel channel: {panel_channel.mention} (**{panel_channel.id}**)\n'
                f'> Channel: {channel.mention} (**{channel.id}**)'
            ),
            color=nextcord.Colour.brand_green(),
            timestamp=datetime.datetime.today()
        )

        embeds.append(embed)
        embed.set_thumbnail(member.display_avatar)
        return Message(embed=embed)

    @on_logs(LogType.tickets)
    async def delete_ticket(
        self,
        owner: nextcord.Member,
        member: nextcord.Member,
        panel_channel_id: int,
        channel: nextcord.TextChannel
    ):
        panel_channel = self.guild.get_channel(panel_channel_id)

        embeds = []
        embed = nextcord.Embed(
            title='Delete ticket',
            description=(
                f'> Owner: **{owner.name}** (**{owner.id}**)\n'
                f'> Member: **{member.name}** (**{member.id}**)\n'
                f'> Panel channel: {panel_channel.mention} (**{panel_channel.id}**)\n'
                f'> Channel: **{channel.name}** (**{channel.id}**)'
            ),
            color=nextcord.Colour.brand_red(),
            timestamp=datetime.datetime.today()
        )

        embeds.append(embed)
        embed.set_thumbnail(member.display_avatar)
        return Message(embed=embed)
