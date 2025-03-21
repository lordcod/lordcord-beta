import contextlib
import nextcord

from bot.databases.varstructs import TicketsPayload
from bot.misc.plugins.tickettools import ModuleTicket
from bot.misc.utils import AsyncSterilization, replace_dict_key
from bot.views.settings.tickets.item.optns.base import ViewOptionItem

from bot.databases import GuildDateBases
from bot.languages import i18n


@AsyncSterilization
class TicketChannelDropDown(nextcord.ui.ChannelSelect):
    async def __init__(
        self,
        guild: nextcord.Guild
    ) -> None:
        gdb = GuildDateBases(guild.id)
        locale = await gdb.get('language')

        super().__init__(placeholder=i18n.t(locale, 'settings.tickets.channels.dropdown.channel'),
                         channel_types=[nextcord.ChannelType.text])

    async def callback(self, interaction: nextcord.Interaction) -> None:
        channel = self.values[0]

        gdb = GuildDateBases(interaction.guild_id)
        tickets: TicketsPayload = await gdb.get('tickets')
        ticket_data = tickets[self.view.message_id]

        with contextlib.suppress(KeyError, AttributeError, nextcord.NotFound):
            old_channel = interaction.guild.get_channel(
                ticket_data['channel_id'])
            old_message = old_channel.get_partial_message(
                ticket_data['message_id'])
            await old_message.delete()

        message = await ModuleTicket.update_message(channel, ticket_data)

        ticket_data['message_id'] = message.id
        ticket_data['channel_id'] = channel.id

        tickets = replace_dict_key(tickets, self.view.message_id, message.id)

        await gdb.set('tickets',  tickets)

        view = await TicketChannelsView(interaction.guild, message.id)
        embed = await view.get_embed(interaction.guild)
        await interaction.response.edit_message(embed=embed, view=view)


@AsyncSterilization
class TicketCategoryDropDown(nextcord.ui.ChannelSelect):
    async def __init__(
        self,
        guild: nextcord.Guild
    ) -> None:
        gdb = GuildDateBases(guild.id)
        locale = await gdb.get('language')

        super().__init__(placeholder=i18n.t(locale, 'settings.tickets.channels.dropdown.category'),
                         channel_types=[nextcord.ChannelType.category])

    async def callback(self, interaction: nextcord.Interaction) -> None:
        category = self.values[0]

        gdb = GuildDateBases(interaction.guild_id)
        tickets: TicketsPayload = await gdb.get('tickets')
        ticket_data = tickets[self.view.message_id]

        ticket_data['category_id'] = category.id
        await gdb.set_on_json('tickets', self.view.message_id,  ticket_data)

        await self.view.update(interaction)


@AsyncSterilization
class TicketClosedCategoryDropDown(nextcord.ui.ChannelSelect):
    async def __init__(
        self,
        guild: nextcord.Guild
    ) -> None:
        gdb = GuildDateBases(guild.id)
        locale = await gdb.get('language')

        super().__init__(
            placeholder=i18n.t(
                locale, 'settings.tickets.channels.dropdown.closed'),
            channel_types=[nextcord.ChannelType.category]
        )

    async def callback(self, interaction: nextcord.Interaction) -> None:
        category = self.values[0]

        gdb = GuildDateBases(interaction.guild_id)
        tickets: TicketsPayload = await gdb.get('tickets')
        ticket_data = tickets[self.view.message_id]

        ticket_data['closed_category_id'] = category.id
        await gdb.set_on_json('tickets', self.view.message_id, ticket_data)

        await self.view.update(interaction)


@AsyncSterilization
class TicketChannelsView(ViewOptionItem):
    label: str = 'settings.tickets.channels.title'
    description: str = 'settings.tickets.channels.description'
    emoji = 'ticfolder'

    async def __init__(
        self,
        guild: nextcord.Guild,
        message_id: int
    ) -> None:
        self.message_id = message_id

        gdb = GuildDateBases(guild.id)
        locale = await gdb.get('language')
        tickets: TicketsPayload = await gdb.get('tickets')
        ticket_data = tickets[message_id]

        super().__init__()

        self.add_item(await TicketChannelDropDown(guild))
        if ticket_data == 1:
            self.add_item(await TicketCategoryDropDown(guild))
            self.add_item(await TicketClosedCategoryDropDown(guild))

        self.back.label = i18n.t(locale, 'settings.button.back')
