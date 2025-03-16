from typing import List, Optional
import nextcord

from bot.misc.tickettools import ModuleTicket
from bot.misc.utils import AsyncSterilization
from bot.resources.info import DEFAULT_TICKET_PAYLOAD, DEFAULT_TICKET_PAYLOAD_RU


from .._view import DefaultSettingsView

from bot.databases import GuildDateBases
from .. import tickets
from bot.languages import i18n


@AsyncSterilization
class TicketsSelectorDropDown(nextcord.ui.ChannelSelect):
    async def __init__(
        self,
        placeholder: str,
        channel_types: List[nextcord.ChannelType],
        guild: nextcord.Guild,
        selected_channel: Optional[nextcord.VoiceChannel] = None,
        selected_category: Optional[nextcord.CategoryChannel] = None
    ) -> None:
        self.guild = guild
        self.selected_channel = selected_channel
        self.selected_category = selected_category

        gdb = GuildDateBases(guild.id)
        locale = await gdb.get('language')

        super().__init__(placeholder=i18n.t(locale, placeholder),
                         channel_types=channel_types)

    async def callback(self, interaction: nextcord.Interaction) -> None:
        view = await TicketsSelectorView(
            interaction.guild,
            self.selected_channel,
            self.selected_category
        )
        await interaction.response.edit_message(embed=view.embed, view=view)
        return await super().callback(interaction)


@AsyncSterilization
class TicketsChannelDropDown(TicketsSelectorDropDown.cls):
    async def __init__(self, *args) -> None:
        await super().__init__('settings.tickets.selector.channel', [nextcord.ChannelType.text], *args)

    async def callback(self, interaction: nextcord.Interaction) -> None:
        channel = self.values[0]
        self.selected_channel = channel
        await super().callback(interaction)


@AsyncSterilization
class TicketsCategoryDropDown(TicketsSelectorDropDown.cls):
    async def __init__(self, *args) -> None:
        await super().__init__('settings.tickets.selector.category', [nextcord.ChannelType.category], *args)

    async def callback(self, interaction: nextcord.Interaction) -> None:
        category = self.values[0]
        self.selected_category = category
        await super().callback(interaction)


@AsyncSterilization
class TicketsSelectorView(DefaultSettingsView):
    embed: nextcord.Embed = None

    async def __init__(
        self,
        guild: nextcord.Guild,
        selected_channel: Optional[nextcord.VoiceChannel] = None,
        selected_category: Optional[nextcord.CategoryChannel] = None
    ) -> None:
        self.selected_channel = selected_channel
        self.selected_category = selected_category

        gdb = GuildDateBases(guild.id)
        locale = await gdb.get('language')

        super().__init__()

        self.add_item(await TicketsChannelDropDown(guild, selected_channel, selected_category))
        self.add_item(await TicketsCategoryDropDown(guild, selected_channel, selected_category))

        if selected_channel is not None:
            self.create.disabled = False

        self.back.label = i18n.t(locale, 'settings.button.back')
        self.create.label = i18n.t(locale, 'settings.button.create')

    @nextcord.ui.button(label='Back', style=nextcord.ButtonStyle.red)
    async def back(self,
                   button: nextcord.ui.Button,
                   interaction: nextcord.Interaction):
        view = await tickets.TicketsView(interaction.guild)
        await interaction.response.edit_message(embed=view.embed, view=view)

    @nextcord.ui.button(label='Create', style=nextcord.ButtonStyle.blurple, disabled=True)
    async def create(self,
                     button: nextcord.ui.Button,
                     interaction: nextcord.Interaction):
        gdb = GuildDateBases(interaction.guild_id)
        locale = await gdb.get('language')

        data = (DEFAULT_TICKET_PAYLOAD_RU if locale == 'ru'
                else DEFAULT_TICKET_PAYLOAD).copy()

        if self.selected_category is not None:
            data.update({'category_id': self.selected_category.id})

        await ModuleTicket.create_ticket_panel(self.selected_channel, data)

        view = await tickets.TicketsView(interaction.guild)
        await interaction.response.edit_message(embed=view.embed, view=view)
