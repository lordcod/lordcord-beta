from typing import Optional
import nextcord

from bot.databases.handlers.guildHD import GuildDateBases
from bot.databases.varstructs import TicketsPayload
from bot.languages import i18n
from bot.misc.utils import AsyncSterilization, is_emoji
from bot.resources.ether import Emoji
from bot.resources.info import DEFAULT_TICKET_PAYLOAD, DEFAULT_TICKET_PAYLOAD_RU
from .base import OptionItem, ViewOptionItem

components_data = {
    'category_placeholder': {
        'type': 'placeholder',
        'label': 'settings.tickets.components.category_placeholder'
    },
    'modal_placeholder': {
        'type': 'placeholder',
        'label': 'settings.tickets.components.modal_placeholder'
    },
    'faq_placeholder': {
        'type': 'placeholder',
        'label': 'settings.tickets.components.faq_placeholder'
    },
    'faq_option': {
        'type': 'option',
        'label': 'settings.tickets.components.faq_option'
    },
    'faq_button_open': {
        'type': 'button',
        'label': 'settings.tickets.components.faq_button_open'
    },
    'faq_button_create': {
        'type': 'button',
        'label': 'settings.tickets.components.faq_button_create'
    },
    'delete_button': {
        'type': 'button',
        'label': 'settings.tickets.components.delete_button'
    },
    'reopen_button': {
        'type': 'button',
        'label': 'settings.tickets.components.reopen_button'
    },
    'close_button': {
        'type': 'button',
        'label': 'settings.tickets.components.close_button'
    },
}
button_styles = {
    nextcord.ButtonStyle.primary: {
        'label': 'settings.tickets.components.button_style.primary',
        'emoji': Emoji.status_streaming
    },
    nextcord.ButtonStyle.secondary: {
        'label': 'settings.tickets.components.button_style.secondary',
        'emoji': Emoji.status_offline
    },
    nextcord.ButtonStyle.success: {
        'label': 'settings.tickets.components.button_style.success',
        'emoji': Emoji.status_online
    },
    nextcord.ButtonStyle.danger: {
        'label': 'settings.tickets.components.button_style.danger',
        'emoji': Emoji.status_dnd
    }
}


@AsyncSterilization
class ComponentsSelectOptionModal(nextcord.ui.Modal):
    async def __init__(
        self,
        guild: nextcord.Guild,
        message_id: int,
        selected_value: str
    ):
        gdb = GuildDateBases(guild.id)
        locale = await gdb.get('language')

        self.guild = guild
        self.message_id = message_id
        self.selected_value = selected_value

        gdb = GuildDateBases(guild.id)
        tickets: TicketsPayload = await gdb.get('tickets')
        ticket_data = tickets[message_id]
        buttons = ticket_data.get('buttons', {})
        option = buttons.get(selected_value)

        label = i18n.t(locale, components_data[selected_value]['label'])

        super().__init__(i18n.t(locale, 'settings.tickets.components.modal.title',
                                label=label))

        self.label = nextcord.ui.TextInput(
            label=i18n.t(locale, 'settings.tickets.components.modal.label'),
            max_length=100,
            placeholder=option.get('label')
        )
        self.add_item(self.label)

        self.emoji = nextcord.ui.TextInput(
            label=i18n.t(locale, 'settings.tickets.components.modal.emoji'),
            required=False,
            max_length=100,
            placeholder=option.get('emoji')
        )
        self.add_item(self.emoji)

        self.description = nextcord.ui.TextInput(
            label=i18n.t(
                locale, 'settings.tickets.components.modal.description'),
            required=False,
            max_length=100,
            placeholder=option.get('description')
        )
        self.add_item(self.description)

    async def callback(self, interaction: nextcord.Interaction) -> None:
        gdb = GuildDateBases(interaction.guild_id)
        locale = await gdb.get('language')
        tickets: TicketsPayload = await gdb.get('tickets')
        ticket_data = tickets[self.message_id]
        buttons = ticket_data.get('buttons', {})
        option = buttons.get(self.selected_value)

        if not is_emoji(self.emoji.value):
            await interaction.response.send_message(i18n.t(locale,
                                                           'settings.set-reaction.error.located'))

        for model in {'label', 'emoji'}:
            value = getattr(self, model).value
            if not value:
                continue
            option[model] = value
        ticket_data['buttons'][self.selected_value] = option

        await gdb.set_on_json('tickets', self.message_id, ticket_data)
        await OptionItem.edit_panel(self, interaction)

        view = await TicketComponentsView(interaction.guild, self.message_id, self.selected_value)
        embed = await view.get_embed(interaction.guild)
        await interaction.response.edit_message(embed=embed, view=view)


@AsyncSterilization
class ComponentsButtonStyleDropDown(nextcord.ui.StringSelect):
    async def __init__(
        self,
        guild: nextcord.Guild,
        message_id: int,
        selected_value: Optional[str] = None
    ):
        gdb = GuildDateBases(guild.id)
        locale = await gdb.get('language')
        tickets: TicketsPayload = await gdb.get('tickets')
        ticket_data = tickets[message_id]
        buttons = ticket_data.get('buttons', {})
        button = buttons.get(selected_value, {})

        self.guild = guild
        self.message_id = message_id
        self.selected_value = selected_value

        if not selected_value or components_data[selected_value]['type'] != 'button':
            options = [nextcord.SelectOption(label='SelectOption')]
            super().__init__(placeholder=i18n.t(locale, 'settings.tickets.components.button_style.dropdown'),
                             options=options,
                             disabled=True)
            return

        options = [
            nextcord.SelectOption(
                label=i18n.t(locale, opt['label']),
                value=style,
                emoji=opt.get('emoji'),
                default=button.get(
                    'style', nextcord.ButtonStyle.secondary) == style
            )
            for style, opt in button_styles.items()
        ]

        super().__init__(placeholder=i18n.t(locale, 'settings.tickets.components.button_style.dropdown'),
                         options=options)

    async def callback(self, interaction: nextcord.Interaction) -> None:
        gdb = GuildDateBases(interaction.guild_id)
        tickets: TicketsPayload = await gdb.get('tickets')
        ticket_data = tickets[self.message_id]
        ticket_data['buttons'][self.selected_value]['style'] = int(
            self.values[0])
        await gdb.set_on_json('tickets', self.message_id, ticket_data)

        await OptionItem.edit_panel(self, interaction)

        view = await TicketComponentsView(interaction.guild, self.message_id, self.selected_value)
        embed = await view.get_embed(interaction.guild)
        await interaction.response.edit_message(embed=embed, view=view)


@AsyncSterilization
class ComponentsButtonModal(nextcord.ui.Modal):
    async def __init__(
        self,
        guild: nextcord.Guild,
        message_id: int,
        selected_value: str
    ):
        gdb = GuildDateBases(guild.id)
        locale = await gdb.get('language')

        self.guild = guild
        self.message_id = message_id
        self.selected_value = selected_value

        gdb = GuildDateBases(guild.id)
        tickets: TicketsPayload = await gdb.get('tickets')
        ticket_data = tickets[message_id]
        buttons = ticket_data.get('buttons', {})
        button = buttons.get(selected_value)

        label = i18n.t(locale, components_data[selected_value]['label'])
        super().__init__(i18n.t(locale, 'settings.tickets.components.modal.title',
                                label=label))

        self.label = nextcord.ui.TextInput(
            label=i18n.t(locale, 'settings.tickets.components.modal.label'),
            max_length=80,
            placeholder=button.get('label')
        )
        self.add_item(self.label)

        self.emoji = nextcord.ui.TextInput(
            label=i18n.t(locale, 'settings.tickets.components.modal.emoji'),
            required=False,
            max_length=100,
            placeholder=button.get('emoji')
        )
        self.add_item(self.emoji)

    async def callback(self, interaction: nextcord.Interaction) -> None:
        gdb = GuildDateBases(interaction.guild_id)
        tickets: TicketsPayload = await gdb.get('tickets')
        ticket_data = tickets[self.message_id]
        buttons = ticket_data.get('buttons', {})
        option = buttons.get(self.selected_value, {})

        for model in {'label', 'emoji'}:
            value = getattr(self, model).value
            if not value:
                continue
            option[model] = value
        ticket_data['buttons'][self.selected_value] = option

        await gdb.set_on_json('tickets', self.message_id, ticket_data)
        await OptionItem.edit_panel(self, interaction)

        view = await TicketComponentsView(interaction.guild, self.message_id, self.selected_value)
        embed = await view.get_embed(interaction.guild)
        await interaction.response.edit_message(embed=embed, view=view)


@AsyncSterilization
class ComponentsPlaceholderModal(nextcord.ui.Modal):
    async def __init__(
        self,
        guild: nextcord.Guild,
        message_id: int,
        selected_value: str
    ):
        gdb = GuildDateBases(guild.id)
        locale = await gdb.get('language')
        tickets: TicketsPayload = await gdb.get('tickets')
        ticket_data = tickets[message_id]
        buttons = ticket_data.get('buttons', {})
        placeholder = buttons.get(selected_value)

        self.guild = guild
        self.message_id = message_id
        self.selected_value = selected_value

        label = i18n.t(locale, components_data[selected_value]['label'])
        super().__init__(i18n.t(locale, 'settings.tickets.components.modal.title',
                                label=label))

        self.placeholder = nextcord.ui.TextInput(
            label=i18n.t(
                locale, 'settings.tickets.components.modal.placeholder'),
            max_length=100,
            placeholder=placeholder
        )
        self.add_item(self.placeholder)

    async def callback(self, interaction: nextcord.Interaction) -> None:
        gdb = GuildDateBases(interaction.guild_id)
        tickets: TicketsPayload = await gdb.get('tickets')
        ticket_data = tickets[self.message_id]
        ticket_data['buttons'][self.selected_value] = self.placeholder.value
        await gdb.set_on_json('tickets', self.message_id, ticket_data)
        await OptionItem.edit_panel(self, interaction)

        view = await TicketComponentsView(interaction.guild, self.message_id, self.selected_value)
        embed = await view.get_embed(interaction.guild)
        await interaction.response.edit_message(embed=embed, view=view)


@AsyncSterilization
class TicketComponentsDropDown(nextcord.ui.StringSelect):
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
            for key, data in components_data.items()
        ]
        super().__init__(placeholder=i18n.t(locale, 'settings.tickets.components.dropdown'),
                         options=options)

    async def callback(self, interaction: nextcord.Interaction) -> None:
        value = self.values[0]

        view = await TicketComponentsView(interaction.guild, self.view.message_id, value)
        embed = await view.get_embed(interaction.guild)
        await interaction.response.edit_message(embed=embed, view=view)


@AsyncSterilization
class TicketComponentsView(ViewOptionItem):
    label: str = "settings.tickets.components.label"
    description: str = "settings.tickets.components.description"
    emoji: str = 'ticmes'

    async def __init__(self, guild: nextcord.Guild, message_id: int, selected_value: Optional[str] = None) -> None:
        gdb = GuildDateBases(guild.id)
        locale = await gdb.get('language')

        self.message_id = message_id
        self.selected_value = selected_value

        super().__init__()

        if selected_value is not None:
            self.edit.disabled = False
            self.reset.disabled = False

        modal = await ComponentsButtonStyleDropDown(guild, message_id, selected_value)
        self.add_item(modal)

        tmdd = await TicketComponentsDropDown(guild, message_id, selected_value)
        self.add_item(tmdd)

        self.back.label = i18n.t(locale, 'settings.button.back')
        self.edit.label = i18n.t(locale, 'settings.button.edit')
        self.reset.label = i18n.t(locale, 'settings.button.reset')

    @nextcord.ui.button(label='Edit', style=nextcord.ButtonStyle.success, disabled=True)
    async def edit(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        compnt_type = components_data[self.selected_value]['type']
        if compnt_type == 'option':
            modal = await ComponentsSelectOptionModal(interaction.guild, self.message_id, self.selected_value)
        elif compnt_type == 'button':
            modal = await ComponentsButtonModal(interaction.guild, self.message_id, self.selected_value)
        elif compnt_type == 'placeholder':
            modal = await ComponentsPlaceholderModal(interaction.guild, self.message_id, self.selected_value)
        else:
            raise TypeError("The %s type was not found" % compnt_type)
        await interaction.response.send_modal(modal)

    @nextcord.ui.button(label='Reset', style=nextcord.ButtonStyle.blurple, disabled=True)
    async def reset(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        gdb = GuildDateBases(interaction.guild_id)
        locale = await gdb.get('language')
        tickets: TicketsPayload = await gdb.get('tickets')
        ticket_data = tickets[self.message_id]

        buttons = ticket_data.get('buttons', {})
        ticket_data['buttons'] = buttons

        default_data = DEFAULT_TICKET_PAYLOAD_RU if locale == 'ru' else DEFAULT_TICKET_PAYLOAD
        buttons[self.selected_value] = default_data['buttons'][self.selected_value]

        await gdb.set_on_json('tickets', self.message_id, ticket_data)
        await self.edit_panel(interaction)

        view = await TicketComponentsView(interaction.guild, self.message_id, self.selected_value)
        embed = await self.get_embed(interaction.guild)
        await interaction.response.edit_message(embed=embed, view=view)
