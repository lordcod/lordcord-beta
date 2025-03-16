import contextlib
from enum import IntEnum
import logging
import nextcord
from bot.databases import localdb
from bot.databases.handlers.guildHD import GuildDateBases
from bot.databases.varstructs import CategoryPayload, TicketsItemPayload, TicketsPayload, UserTicketPayload
from typing import Dict,  List, Literal, Optional, Self, Tuple

from bot.languages import i18n
from bot.misc import logstool, utils
from bot.misc.utils import generate_message, get_payload, lord_format
from bot.misc.lordbot import LordBot
from bot.resources.ether import Emoji
from bot.views.tickets.categories import CategoryView
from bot.views.tickets.closes import CloseTicketView
from bot.views.tickets.delop import ControllerTicketView
from bot.views.tickets.faq import FAQView
from bot.views.tickets.modals import TicketsModal
from bot.resources.info import (
    DEFAULT_TICKET_LIMIT,
    DEFAULT_TICKET_PAYLOAD,
    DEFAULT_TICKET_PAYLOAD_RU,
    DEFAULT_TICKET_PERMISSIONS,
    DEFAULT_TICKET_TYPE
)

_log = logging.getLogger(__name__)


class TicketStatus(IntEnum):
    opened = 1
    closed = 2
    deleted = 3
    predelete = 4


def parse_permissions_string(permission_data: dict, mod_roles: list, guild_id: int, owner_id: int):
    data = {}
    for key in list(permission_data.keys()):
        if not isinstance(key, str):
            continue

        value = permission_data.pop(key)
        key = key.lower()

        if key == 'moderator':
            data.update(
                {role: value for role in mod_roles}
            )
        if key == 'everyone':
            data[guild_id] = value
        if key == 'owner':
            data[owner_id] = value


class ModuleTicket:
    # TODO: Add logs

    locale: Optional[str] = None
    settings_message = None
    selected_category: Optional[CategoryPayload] = None
    input_answer: Optional[Dict[str, str]] = None
    status: Optional[TicketStatus] = None
    owner: Optional[nextcord.Member] = None
    messages: Optional[List] = None

    def __init__(
        self,
        member: nextcord.Member,
        message_id: int
    ) -> None:
        guild = member.guild
        client: LordBot = guild._state._get_client()
        self.member = member
        self.guild = guild
        self.gdb = GuildDateBases(guild.id)
        self.lord_handler = client.lord_handler_timer
        self.loop = guild._state.loop
        self.message_id = message_id

    async def get_locale(self) -> str:
        if self.locale is not None:
            return self.locale

        self.locale = await self.gdb.get('language')

    @classmethod
    async def from_channel_id(cls, member: nextcord.Member, channel: nextcord.TextChannel) -> Self:
        tickets_data = await localdb.get_table('tickets')
        ticket_data = await tickets_data.get(channel.id)
        message_id = ticket_data['ticket_id']
        self = cls(member, message_id)
        self.ticket_channel = channel
        guild_data = await self.fetch_ticket_data()
        self.update_from_ticket_data(guild_data)
        return self

    @staticmethod
    async def create_ticket_panel(channel: nextcord.TextChannel, ticket_data: Optional[TicketsItemPayload] = None):
        gdb = GuildDateBases(channel.guild.id)
        locale = await gdb.get('language')

        if ticket_data is None:
            ticket_data = (DEFAULT_TICKET_PAYLOAD_RU if locale == 'ru'
                           else DEFAULT_TICKET_PAYLOAD).copy()

        message = await ModuleTicket.update_message(channel, ticket_data)

        ticket_data['enabled'] = True
        ticket_data['message_id'] = message.id
        ticket_data['channel_id'] = channel.id
        if 'category_id' not in ticket_data:
            ticket_data['category_id'] = channel.category_id

        await gdb.set_on_json('tickets', message.id, ticket_data)

    @staticmethod
    async def update_ticket_panel(guild: nextcord.Guild, message_id: int):
        gdb = GuildDateBases(guild.id)
        tickets: TicketsPayload = await gdb.get('tickets', {})
        ticket_data = tickets.get(message_id)

        channel_id = ticket_data['channel_id']
        channel = guild.get_channel(channel_id)

        await ModuleTicket.update_message(channel, ticket_data, message_id)

    @staticmethod
    async def update_message(channel: nextcord.TextChannel, ticket_data: TicketsItemPayload, message_id: Optional[int] = None) -> nextcord.Message:
        panel_message = ticket_data['messages']['panel']
        msg_data = utils.generate_message(utils.lord_format(
            panel_message, get_payload(guild=channel.guild)))
        view = await FAQView(channel.guild.id, ticket_data)

        message = None
        if message_id is not None:
            message = channel.get_partial_message(message_id)

        if message is not None:
            try:
                message = await message.edit(**msg_data, view=view)
            except nextcord.NotFound:
                return

        if message is None:
            message = await channel.send(**msg_data, view=view)

        return message

    async def fetch_guild_ticket(self):
        gdb = GuildDateBases(self.guild.id)
        tickets: TicketsPayload = await gdb.get('tickets', {})
        ticket_data = tickets.get(self.message_id)
        return ticket_data

    async def fetch_ticket_data(self):
        tickets_data = await localdb.get_table('tickets')
        return await tickets_data.get(self.ticket_channel.id)

    async def set_ticket_data(self, data=None):
        if data is None:
            data = self.get_ticket_data()
        tickets_data = await localdb.get_table('tickets')
        await tickets_data.set(self.ticket_channel.id, data)

    async def get_ticket_data_from_member(self, category: Optional[CategoryPayload] = None) -> List[UserTicketPayload]:
        tickets_data = await localdb.get_table('tickets')
        keys = await self.get_ticket_keys()
        tickets: List[UserTicketPayload] = await tickets_data.multi_get(keys)
        ret = []

        for i, ticket in enumerate(tickets):
            if ticket is None:
                keys.pop(i)
                tickets.pop(i)
                continue
            if ticket['owner_id'] == self.member.id:
                if (ticket['status'] != TicketStatus.opened
                        or (category and ticket['category'] and category != ticket['category'])):
                    continue
                ticket['channel_id'] = keys[i]
                ret.append(ticket)
        await tickets_data.multi_set(list(zip(keys, tickets)))
        return ret

    async def get_ticket_count(self):
        tickets_data = await localdb.get_table('tickets')
        keys = await self.get_ticket_keys()
        tickets: List[UserTicketPayload] = await tickets_data.multi_get(keys)

        total = len(tickets)+1
        active = 1

        for ticket in tickets:
            if ticket['status'] == TicketStatus.opened:
                active += 1

        return {
            'total': total,
            'active': active
        }

    async def get_ticket_keys(self):
        tickets_data_panel = await localdb.get_table('tickets-panel')
        channels = await tickets_data_panel.get(self.message_id, [])
        return channels

    async def remove_ticket_count(self):
        tickets_data_panel = await localdb.get_table('tickets-panel')
        channels = await tickets_data_panel.get(self.message_id, [])
        with contextlib.suppress(IndexError):
            channels.remove(self.ticket_channel.id)
        await tickets_data_panel.set(self.message_id, channels)

    async def increment_ticket_count(self):
        tickets_data_panel = await localdb.get_table('tickets-panel')
        channels = await tickets_data_panel.get(self.message_id, [])
        channels.append(self.ticket_channel.id)
        await tickets_data_panel.set(self.message_id, channels)

    def get_ticket_data(self) -> UserTicketPayload:
        return {
            'owner_id': self.owner.id,
            'channel_id': self.ticket_channel.id,
            'ticket_id': self.message_id,
            'category': self.selected_category,
            'inputs': self.input_answer,
            'status': self.status,
            'count': self.ticket_count,
            'messages': self.messages
        }

    def update_from_ticket_data(self, data: UserTicketPayload):
        self.owner = self.guild.get_member(data['owner_id'])
        self.message_id = data['ticket_id']
        self.selected_category = data['category']
        self.input_answer = data['inputs']
        self.status = TicketStatus(data['status'])
        try:
            self.ticket_count = data['count']
        except KeyError:
            self.ticket_count = {
                'total': data['index'],
                'active': data['index']
            }
        self.messages = data.get('messages', [])

    async def get_permissions(self, permission_data: Dict[int, Tuple[int, int]]):
        ticket_data = await self.fetch_guild_ticket()
        mod_roles = ticket_data.get('moderation_roles', [])
        guild_id = self.guild.id
        owner_id = self.member.id

        if not permission_data:
            permission_data = DEFAULT_TICKET_PERMISSIONS.copy()

        parse_permissions_string(
            permission_data, mod_roles, guild_id, owner_id)
        parsed_data = {}
        for id, (allow, deny) in permission_data.items():
            key = self.guild.get_member(id) or self.guild.get_role(id)
            overwrite = nextcord.PermissionOverwrite.from_pair(
                nextcord.Permissions(allow),
                nextcord.Permissions(deny)
            )
            if key is None:
                continue
            parsed_data[key] = overwrite
        return parsed_data

    async def create(self) -> None:
        ticket_data = await self.fetch_guild_ticket()
        self.ticket_count = await self.get_ticket_count()
        locale = await self.get_locale()
        category_payload = self.selected_category

        if category_payload:
            def get_data(key, default=None):
                return category_payload.get(key) or ticket_data.get(key) or default
        else:
            get_data = ticket_data.get

        buttons = get_data('buttons')
        open_name = get_data('names').get('open')
        open_message = get_data('messages').get('open')
        ticket_type = get_data('type', DEFAULT_TICKET_TYPE)
        channel_id = get_data('channel_id')
        payload = get_payload(
            member=self.member,
            inputs=self.input_answer,
            category=self.selected_category,
            ticket_count=self.ticket_count
        )

        name = utils.lord_format(open_name, payload)
        message = utils.generate_message(
            utils.lord_format(open_message, payload))
        view = await CloseTicketView(self.guild.id, buttons)

        channel: nextcord.TextChannel = self.guild.get_channel(channel_id)

        msg_embeds = message.pop('embeds', [])
        if self.input_answer and get_data('creating_embed_inputs'):
            embed = nextcord.Embed(
                title=i18n.t(locale, 'tickets.modal'),
                color=2829617,
                description='\n'.join(
                    f"**{label}**```\n{res}```"
                    for label, res in self.input_answer.items()
                )
            )
            msg_embeds.append(embed)
            if msg_embed := message.pop('embed', None):
                message['embeds'].insert(0, msg_embed)

        if ticket_type == 1:
            _log.trace('Getted category: %s, Channel category: %s',
                       get_data('category_id'), channel.category)
            category_id = get_data('category_id')
            category: nextcord.CategoryChannel = self.guild.get_channel(
                category_id)
            self.ticket_channel = channel = await self.guild.create_text_channel(
                name=name,
                category=category,
                topic=i18n.t(locale, 'tickets.topic.open',
                             member=self.member.name),
                overwrites=await self.get_permissions(get_data('permissions'))
            )
            msg = await channel.send(**message, view=view)
        elif ticket_type == 2:
            self.ticket_channel = thread = await channel.create_thread(
                name=name,
                auto_archive_duration=get_data('auto_archived'),
                type=nextcord.ChannelType.private_thread,
                invitable=False,
            )
            msg = await thread.send(**message, embeds=msg_embeds, view=view)
            if mod_roles := [role.mention for role_id in get_data('moderation_roles', [])
                             if (role := self.guild.get_role(role_id))]:
                await thread.send(' '.join(mod_roles),
                                  delete_after=1,
                                  flags=nextcord.MessageFlags(suppress_notifications=True))

        _log.trace('Created ticket channel %s', self.ticket_channel)
        self.status = TicketStatus.opened
        self.owner = self.member

        await msg.pin()
        await self.set_ticket_data()
        await self.increment_ticket_count()
        await self.settings_message.edit(i18n.t(locale, 'tickets.message.open', channel=self.ticket_channel.mention),
                                         embeds=[], view=None)

        await logstool.Logs(self.guild).create_ticket(
            self.member,
            ticket_data.get('channel_id'),
            self.ticket_channel,
            self.input_answer,
            self.selected_category and self.selected_category['label'],
            self.ticket_count
        )

    async def create_after_modals(self, interaction: nextcord.Interaction, modals: Optional[dict] = None):
        if self.settings_message is None:
            self.settings_message = await interaction.response.send_message(f'{Emoji.loading} Loading...', ephemeral=True)
        # TODO: change to modals and not categories_data
        elif not interaction.response._responded:
            await interaction.response.defer()
        self.input_answer = modals
        await self.create()

    async def create_after_category(self, interaction: nextcord.Interaction, category: Optional[CategoryPayload] = None):
        tickets = await self.get_ticket_data_from_member(category)
        ticket_data = await self.fetch_guild_ticket()
        locale = await self.get_locale()
        categories_data = ticket_data.get('categories')
        buttons = ticket_data.get('buttons')
        user_tickets_limit = (category and category.get(
            'user_tickets_limit')) or ticket_data.get('user_tickets_limit') or DEFAULT_TICKET_LIMIT
        self.selected_category = category

        if category is None:
            approved_roles = ticket_data.get('approved_roles')
        else:
            if 'approved_roles' in category:
                approved_roles = category['approved_roles']
            elif 'approved_roles' in ticket_data:
                approved_roles = ticket_data['approved_roles']
            else:
                approved_roles = None

        if category and category.get('modals'):
            modals = category.get('modals')
        else:
            modals = ticket_data.get('modals')

        def send_message(content: str):
            if not modals or categories_data:
                return self.settings_message.edit(content=content, view=None, embed=None)
            else:
                return interaction.response.send_message(content, ephemeral=True)

        if approved_roles is not None and not set(interaction.user._roles) & set(approved_roles):
            await send_message(i18n.t(locale, 'tickets.error.approved_roles',
                                      roles=', '.join([role.mention for role_id in approved_roles if (role := interaction.guild.get_role(role_id))])))
            return

        if len(tickets) >= user_tickets_limit:
            if category is not None:
                await send_message(i18n.t(locale, 'tickets.error.limit.category',
                                          category=category.get('label'),
                                          count=len(tickets)))
            else:
                await send_message(i18n.t(locale, 'tickets.error.limit.global',
                                          count=len(tickets)))
            return

        if not modals:
            await self.create_after_modals(interaction)
            return

        modal = await TicketsModal(self, buttons)
        await interaction.response.send_modal(modal)

        if self.settings_message and categories_data:
            view = await CategoryView(self, buttons)
            await self.settings_message.edit(content=None, view=view)

    async def create_after_faq(self, interaction: nextcord.Interaction):
        tickets = await self.get_ticket_data_from_member()
        ticket_data = await self.fetch_guild_ticket()
        locale = await self.get_locale()
        categories_data = ticket_data.get('categories')
        modals = ticket_data.get('modals')
        buttons = ticket_data.get('buttons')
        category_message = ticket_data.get('messages').get('category')

        if ticket_data.get('global_user_tickets_limit') and len(tickets) >= ticket_data.get('global_user_tickets_limit'):
            await interaction.response.send_message(i18n.t(locale, 'tickets.error.limit.global',
                                                           count=len(tickets)),
                                                    ephemeral=True)
            return
        if not modals or categories_data:
            self.settings_message = await interaction.response.send_message(i18n.t(locale, 'tickets.message.loading'), ephemeral=True)
        if not categories_data:
            await self.create_after_category(interaction)
            return

        if category_message is not None:
            payload = get_payload(member=interaction.user)
            message = generate_message(lord_format(category_message, payload))
            if 'content' not in message:
                message['content'] = None
        else:
            message = {'content': None}

        view = await CategoryView(self, buttons)
        await self.settings_message.edit(**message, view=view)

    async def close(self):
        ticket_data = await self.fetch_guild_ticket()
        locale = await self.get_locale()
        category_payload = self.selected_category

        if category_payload:
            def get_data(key, default=None):
                return category_payload.get(key) or ticket_data.get(key) or default
        else:
            get_data = ticket_data.get

        payload = get_payload(
            member=self.member,
            inputs=self.input_answer,
            category=self.selected_category,
            ticket_count=self.ticket_count
        )

        buttons = get_data('buttons')
        ticket_type = get_data('type', DEFAULT_TICKET_TYPE)
        user_closed = get_data('user_closed', True)
        name = get_data('names').get('close')
        message = get_data('messages')['close']
        ctrl_message_data = get_data('messages')['controller']

        ctrl_message = utils.generate_message(
            utils.lord_format(ctrl_message_data, payload))
        close_message = utils.generate_message(
            utils.lord_format(message, payload))
        close_name = name and utils.lord_format(name, payload)

        view = await ControllerTicketView(self.guild.id, buttons)

        if (not self._is_verification(get_data, user_closed)
                or self.status != TicketStatus.opened):
            return

        await self.ticket_channel.send(**close_message)
        await self.ticket_channel.send(**ctrl_message, view=view)

        editted_data = None

        if ticket_type == 1:
            closed_category_id = get_data('closed_category_id')
            closed_category = self.guild.get_channel(closed_category_id)
            editted_data = dict(
                name=close_name,
                topic=self.ticket_channel.topic +
                i18n.t(locale, 'tickets.topic.close', member=self.member.name)
            )
            if closed_category:
                editted_data['category'] = closed_category
        elif ticket_type == 2:
            editted_data = dict(name=close_name)

        if name is None:
            editted_data.pop('name')
        if editted_data:
            await self.ticket_channel.edit(**editted_data)

        self.status = TicketStatus.closed
        await self.set_ticket_data()

        await logstool.Logs(self.guild).close_ticket(
            self.owner,
            self.member,
            ticket_data.get('channel_id'),
            self.ticket_channel
        )

    async def reopen(self, inter_message: nextcord.PartialInteractionMessage):
        self.lord_handler.close(f'ticket-delete:{self.ticket_channel.id}')

        ticket_data = await self.fetch_guild_ticket()
        locale = await self.get_locale()
        category_payload = self.selected_category

        if category_payload:
            def get_data(key, default=None):
                return category_payload.get(key) or ticket_data.get(key) or default
        else:
            get_data = ticket_data.get

        payload = get_payload(
            member=self.member,
            inputs=self.input_answer,
            category=self.selected_category,
            ticket_count=self.ticket_count
        )

        ticket_type = get_data('type', DEFAULT_TICKET_TYPE)
        message = get_data('messages')['reopen']
        name = get_data('names')['open']
        close_name = get_data('names').get('close')

        reopen_message = utils.generate_message(
            utils.lord_format(message, payload))
        reopen_name = utils.lord_format(name, payload)

        if not (self._is_verification(get_data)
                and self.status in (TicketStatus.closed, TicketStatus.predelete)):
            return

        await self.ticket_channel.send(**reopen_message)

        editted_data = None

        if ticket_type == 1:
            closed_category_id = get_data('closed_category_id')
            category_id = get_data('category_id')
            category = self.guild.get_channel(category_id)
            editted_data = dict(
                name=reopen_name,
                topic=self.ticket_channel.topic +
                i18n.t(locale, 'tickets.topic.reopen', member=self.member.name)
            )
            if closed_category_id and category:
                editted_data['category'] = category
        elif ticket_type == 2:
            editted_data = dict(name=reopen_name)

        if close_name is None:
            editted_data.pop('name')
        if editted_data:
            await self.ticket_channel.edit(**editted_data)

        self.status = TicketStatus.opened
        await self.set_ticket_data()
        await inter_message.delete()

        await logstool.Logs(self.guild).reopen_ticket(
            self.owner,
            self.member,
            ticket_data.get('channel_id'),
            self.ticket_channel
        )

    async def delete(self):
        ticket_data = await self.fetch_guild_ticket()
        category_payload = self.selected_category

        if category_payload:
            def get_data(key, default=None):
                return category_payload.get(key) or ticket_data.get(key) or default
        else:
            get_data = ticket_data.get

        payload = get_payload(
            member=self.member,
            inputs=self.input_answer,
            category=self.selected_category,
            ticket_count=self.ticket_count
        )

        user_closed = get_data('user_closed', True)
        message = get_data('messages')['delete']

        delete_message = utils.generate_message(
            utils.lord_format(message, payload))

        if (not self._is_verification(get_data, user_closed)
                or self.status != TicketStatus.closed):
            return

        await self.ticket_channel.send(**delete_message)
        self.lord_handler.create(
            15,
            self.__delete(),
            f'ticket-delete:{self.ticket_channel.id}'
        )

        self.status = TicketStatus.predelete
        await self.set_ticket_data()

        await logstool.Logs(self.guild).delete_ticket(
            self.owner,
            self.member,
            ticket_data.get('channel_id'),
            self.ticket_channel
        )

    async def __delete(self):
        self.status = TicketStatus.deleted
        await self.set_ticket_data()
        await self.ticket_channel.delete()

    def _is_verification(self, get_data, with_user: bool = True) -> Literal[1, 2]:
        mod_roles = get_data('moderation_roles')
        return (self.member == self.owner and with_user) or bool(mod_roles and set(self.member._roles) & set(mod_roles))

    @classmethod
    async def archive_message(cls, message: nextcord.Message):
        return

        if message.author.bot:
            return

        try:
            self = await cls.from_channel_id(message.author, message.channel)
        except Exception:
            return

        if self.messages is None:
            self.messages = []
        self.messages.append({
            'content': message.content,
            'username': message.author.name
        })

        await self.set_ticket_data()
