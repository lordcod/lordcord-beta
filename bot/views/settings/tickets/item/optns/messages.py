from typing import Optional
import nextcord
import orjson

from bot.databases.handlers.guildHD import GuildDateBases
from bot.databases.varstructs import TicketsPayload
from bot.languages import i18n
from bot.misc.utils import AsyncSterilization, generate_message, get_payload, lord_format
from bot.resources.ether import Emoji
from bot.resources.info import DEFAULT_TICKET_PAYLOAD, DEFAULT_TICKET_PAYLOAD_RU
from .base import OptionItem, ViewOptionItem

messages_data = {
    'panel': {
        'label': 'settings.tickets.messages.panel',
        'emoji': Emoji.envelope_panel
    },
    'open': {
        'label': 'settings.tickets.messages.open',
        'emoji': Emoji.envelope_create
    },
    'category': {
        'label': 'settings.tickets.messages.category',
        'emoji': Emoji.envelope_complete
    }
}


@AsyncSterilization
class TicketMessagesModal(nextcord.ui.Modal, OptionItem):
    async def __init__(
        self,
        guild: nextcord.Guild,
        message_id: int,
        selected_value: str
    ):
        gdb = GuildDateBases(guild.id)
        locale = await gdb.get('language')

        self.message_id = message_id
        self.selected_value = selected_value

        gdb = GuildDateBases(guild.id)
        tickets: TicketsPayload = await gdb.get('tickets')
        ticket_data = tickets[message_id]
        messages = ticket_data.get('messages', {})
        message = messages.get(selected_value)

        if not isinstance(message, str):
            message = orjson.dumps(message).decode()

        label = i18n.t(locale, messages_data[selected_value]['label'])

        super().__init__(i18n.t(locale, 'settings.tickets.messages.modal',
                                label=label))

        self.message = nextcord.ui.TextInput(
            label=label,
            style=nextcord.TextInputStyle.paragraph,
            required=False,
            default_value=message
        )
        self.add_item(self.message)

    async def callback(self, interaction: nextcord.Interaction) -> None:
        gdb = GuildDateBases(interaction.guild_id)
        tickets: TicketsPayload = await gdb.get('tickets')
        ticket_data = tickets[self.message_id]
        ticket_data['messages'][self.selected_value] = self.message.value
        await gdb.set_on_json('tickets', self.message_id, ticket_data)

        if self.selected_value == 'panel':
            await self.edit_panel(interaction)

        view = await TicketMessagesView(interaction.guild, self.message_id, self.selected_value)
        embed = await view.get_embed(interaction.guild)
        await interaction.response.edit_message(embed=embed, view=view)


@AsyncSterilization
class TicketMessagesDropDown(nextcord.ui.StringSelect):
    async def __init__(
        self,
        guild: nextcord.Guild,
        message_id: int,
        selected_value: Optional[str] = None
    ) -> None:
        gdb = GuildDateBases(guild.id)
        locale = await gdb.get('language')

        options = [
            nextcord.SelectOption(
                label=i18n.t(locale, data['label']),
                value=key,
                default=key == selected_value,
                emoji=data.get('emoji')
            )
            for key, data in messages_data.items()
        ]
        super().__init__(placeholder=i18n.t(locale, 'settings.tickets.messages.dropdown'),
                         options=options)

    async def callback(self, interaction: nextcord.Interaction) -> None:
        value = self.values[0]

        view = await TicketMessagesView(interaction.guild, self.view.message_id, value)
        embed = await view.get_embed(interaction.guild)
        await interaction.response.edit_message(embed=embed, view=view)


@AsyncSterilization
class TicketMessagesView(ViewOptionItem):
    label: str = "settings.tickets.messages.label"
    description: str = "settings.tickets.messages.description"
    emoji: str = 'ticmes'

    async def __init__(self, guild: nextcord.Guild, message_id: int, selected_value: Optional[str] = None) -> None:
        gdb = GuildDateBases(guild.id)
        locale = await gdb.get('language')

        self.message_id = message_id
        self.selected_value = selected_value

        super().__init__()

        if selected_value is not None:
            self.preview.disabled = False
            self.edit.disabled = False
            self.reset.disabled = False

        tmdd = await TicketMessagesDropDown(guild, message_id, selected_value)
        self.add_item(tmdd)

        self.back.label = i18n.t(locale, 'settings.button.back')
        self.preview.label = i18n.t(locale, 'settings.button.preview')
        self.edit.label = i18n.t(locale, 'settings.button.edit')
        self.reset.label = i18n.t(locale, 'settings.button.reset')

    @nextcord.ui.button(label='Preview', style=nextcord.ButtonStyle.grey, disabled=True)
    async def preview(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        gdb = GuildDateBases(interaction.guild_id)
        locale = await gdb.get('language')
        tickets: TicketsPayload = await gdb.get('tickets')
        ticket_data = tickets[self.message_id]
        messages = ticket_data.get('messages', {})

        message_data = messages.get(self.selected_value)
        if message_data is not None and len(message_data) > 0:
            payload = get_payload(member=interaction.user)
            message = generate_message(lord_format(message_data, payload))
        else:
            message = {'content': i18n.t(
                locale, 'settings.tickets.messages.error.null')}

        await interaction.response.send_message(**message, ephemeral=True)

    @nextcord.ui.button(label='Edit', style=nextcord.ButtonStyle.success, disabled=True)
    async def edit(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        modal = await TicketMessagesModal(interaction.guild, self.message_id, self.selected_value)
        await interaction.response.send_modal(modal)

    @nextcord.ui.button(label='Reset', style=nextcord.ButtonStyle.blurple, disabled=True)
    async def reset(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        gdb = GuildDateBases(interaction.guild_id)
        locale = await gdb.get('language')
        tickets: TicketsPayload = await gdb.get('tickets')
        ticket_data = tickets[self.message_id]

        messages = ticket_data.get('messages', {})
        ticket_data['messages'] = messages

        default_data = DEFAULT_TICKET_PAYLOAD_RU if locale == 'ru' else DEFAULT_TICKET_PAYLOAD
        messages[self.selected_value] = default_data['messages'][self.selected_value]
        await gdb.set_on_json('tickets', self.message_id, ticket_data)

        if self.selected_value == 'panel':
            await self.edit_panel(interaction)

        view = await TicketMessagesView(interaction.guild, self.message_id, self.selected_value)
        embed = await self.get_embed(interaction.guild)
        await interaction.response.edit_message(embed=embed, view=view)
