import contextlib
from typing import Optional
import nextcord

from bot.databases.handlers.guildHD import GuildDateBases
from bot.databases.varstructs import TicketsPayload
from bot.languages import i18n
from bot.misc.utils import AsyncSterilization
from .base import ViewOptionItem


@AsyncSterilization
class TicketCategoriesModal(nextcord.ui.Modal):
    async def __init__(
        self,
        guild: nextcord.Guild,
        message_id: int,
        selected_value: Optional[int] = None
    ):
        self.message_id = message_id
        self.selected_value = selected_value

        gdb = GuildDateBases(guild.id)
        locale = await gdb.get('language')
        tickets: TicketsPayload = await gdb.get('tickets')
        ticket_data = tickets[message_id]
        categories = ticket_data.get('categories', [])

        def get_data(name):
            if selected_value is not None:
                return categories[selected_value].get(name)

        super().__init__(i18n.t(locale, 'settings.tickets.categories.modal.title'))

        self.label = nextcord.ui.TextInput(
            label=i18n.t(locale, 'settings.tickets.categories.modal.label'),
            max_length=45,
            placeholder=get_data('label'),
            required=not get_data('label')
        )
        self.add_item(self.label)

        self.emoji = nextcord.ui.TextInput(
            label=i18n.t(locale, 'settings.tickets.categories.modal.emoji'),
            required=False,
            max_length=100,
            placeholder=get_data('emoji')
        )
        self.add_item(self.emoji)

        self.description = nextcord.ui.TextInput(
            label=i18n.t(
                locale, 'settings.tickets.categories.modal.description'),
            style=nextcord.TextInputStyle.paragraph,
            required=False,
            max_length=100,
            placeholder=get_data('description')
        )
        self.add_item(self.description)

    async def callback(self, interaction: nextcord.Interaction) -> None:
        gdb = GuildDateBases(interaction.guild_id)
        tickets: TicketsPayload = await gdb.get('tickets')
        ticket_data = tickets[self.message_id]
        categories = ticket_data.setdefault('categories', [])

        if self.selected_value is not None:
            category = categories[self.selected_value]
        else:
            category = {}

        data = dict(
            label=self.label.value,
            emoji=self.emoji.value,
            description=self.description.value
        )
        for key, value in data.items():
            if key != 'label' and value.lower().strip() in ('none', '-'):
                category.pop(key, None)
                continue
            if value:
                category[key] = value

        if self.selected_value is not None:
            try:
                categories[self.selected_value] = category
            except IndexError:
                self.selected_value = len(categories)
                categories.append(category)
        else:
            self.selected_value = len(categories)
            categories.append(category)

        await gdb.set_on_json('tickets', self.message_id, ticket_data)

        view = await TicketCategoriesView(interaction.guild, self.message_id, self.selected_value)
        embed = await view.get_embed(interaction.guild)
        await interaction.response.edit_message(embed=embed, view=view)


@AsyncSterilization
class TicketCategoriesDropDown(nextcord.ui.StringSelect):
    async def __init__(
        self,
        guild: nextcord.Guild,
        message_id: int,
        selected_value: Optional[str] = None
    ) -> None:
        gdb = GuildDateBases(guild.id)
        locale = await gdb.get('language')
        tickets: TicketsPayload = await gdb.get('tickets')
        ticket_data = tickets[message_id]
        categories = ticket_data.get('categories', [])

        options = [
            nextcord.SelectOption(
                label=data['label'][:100],
                value=i,
                default=i == selected_value,
                emoji=data.get('emoji'),
                description=data.get('description', '')[:100]
            )
            for i, data in enumerate(categories)
        ]

        disabled = len(options) == 0
        if disabled:
            options.append(nextcord.SelectOption(label='SelectOption'))

        super().__init__(placeholder=i18n.t(locale, 'settings.tickets.categories.dropdown'),
                         options=options,
                         disabled=disabled)

    async def callback(self, interaction: nextcord.Interaction) -> None:
        value = int(self.values[0])

        view = await TicketCategoriesView(interaction.guild, self.view.message_id, value)
        embed = await view.get_embed(interaction.guild)
        await interaction.response.edit_message(embed=embed, view=view)


@AsyncSterilization
class TicketCategoriesView(ViewOptionItem):
    label: str = "settings.tickets.categories.title"
    description: str = "settings.tickets.categories.description"
    emoji: str = 'ticdone'

    async def __init__(self, guild: nextcord.Guild, message_id: int, selected_value: Optional[str] = None) -> None:
        gdb = GuildDateBases(guild.id)
        locale = await gdb.get('language')

        self.message_id = message_id
        self.selected_value = selected_value

        super().__init__()

        if selected_value is not None:
            self.edit.disabled = False
            self.delete.disabled = False

        tсdd = await TicketCategoriesDropDown(guild, message_id, selected_value)
        self.add_item(tсdd)

        self.back.label = i18n.t(locale, 'settings.button.back')
        self.add.label = i18n.t(locale, 'settings.button.add')
        self.edit.label = i18n.t(locale, 'settings.button.edit')
        self.delete.label = i18n.t(locale, 'settings.button.delete')

    @nextcord.ui.button(label='Add', style=nextcord.ButtonStyle.success)
    async def add(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        modal = await TicketCategoriesModal(interaction.guild, self.message_id)
        await interaction.response.send_modal(modal)

    @nextcord.ui.button(label='Edit', style=nextcord.ButtonStyle.blurple, disabled=True)
    async def edit(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        modal = await TicketCategoriesModal(interaction.guild, self.message_id, self.selected_value)
        await interaction.response.send_modal(modal)

    @nextcord.ui.button(label='Delete', style=nextcord.ButtonStyle.danger, disabled=True)
    async def delete(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        gdb = GuildDateBases(interaction.guild_id)
        tickets: TicketsPayload = await gdb.get('tickets')
        ticket_data = tickets[self.message_id]
        categories = ticket_data.get('categories', [])

        with contextlib.suppress(IndexError):
            categories.pop(self.selected_value)

        await gdb.set_on_json('tickets', self.message_id, ticket_data)

        view = await TicketCategoriesView(interaction.guild, self.message_id)
        embed = await self.get_embed(interaction.guild)
        await interaction.response.edit_message(embed=embed, view=view)
