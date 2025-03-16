import contextlib
import nextcord

from bot.databases import localdb
from bot.databases.handlers.guildHD import GuildDateBases
from bot.databases.varstructs import TicketsPayload, UserTicketPayload
from bot.languages import i18n
from bot.misc.utils import AsyncSterilization
from bot.resources.info import DEFAULT_TICKET_TYPE
from bot.views.settings import tickets as tickets_view
from bot.views.settings._view import DefaultSettingsView
from bot.views.settings.tickets.item.dropdown import TicketsItemDropDown
from bot.views.settings.tickets.item.embeds import get_embed


async def delete_every_tickets(guild: nextcord.Guild, message_id: int):
    tickets_data_panel = await localdb.get_table('tickets-panel')
    tickets_data = await localdb.get_table('tickets')
    keys = await tickets_data_panel.get(message_id, [])
    tickets: list[UserTicketPayload] = await tickets_data.multi_get(keys)

    channels = []

    for ticket in tickets:
        channel = guild.get_channel_or_thread(ticket['channel_id'])
        if channel is not None:
            guild._state.loop.create_task(channel.delete())
            channels.append(channel)

    return channels


@AsyncSterilization
class TicketsItemView(DefaultSettingsView):
    embed = None

    async def __init__(self, guild: nextcord.Guild, message_id: int) -> None:
        gdb = GuildDateBases(guild.id)
        locale = await gdb.get('language')
        tickets: TicketsPayload = await gdb.get('tickets', {})
        ticket_data = tickets[message_id]

        self.message_id = message_id
        self.ticket_data = ticket_data

        enabled = self.ticket_data.get('enabled')

        self.embed = await get_embed(guild, message_id)
        super().__init__()

        tidd = await TicketsItemDropDown(guild, message_id)
        self.add_item(tidd)

        if enabled:
            self.switch.label = i18n.t(locale, 'settings.button.disable')
            self.switch.style = nextcord.ButtonStyle.danger
        else:
            self.switch.label = i18n.t(locale, 'settings.button.enable')
            self.switch.style = nextcord.ButtonStyle.success

        self.back.label = i18n.t(locale, 'settings.button.back')
        self.delete.label = i18n.t(locale, 'settings.button.delete')
        self.delete_with_chls.label = i18n.t(
            locale, 'settings.button.delete_with_chls')

    @nextcord.ui.button(label='Back', style=nextcord.ButtonStyle.red)
    async def back(self,
                   button: nextcord.ui.Button,
                   interaction: nextcord.Interaction):
        view = await tickets_view.TicketsView(interaction.guild)
        await interaction.response.edit_message(embed=view.embed, view=view)

    @nextcord.ui.button()
    async def switch(self, button: nextcord.Button, interaction: nextcord.Interaction):
        self.ticket_data['enabled'] = not self.ticket_data.get('enabled')

        gdb = GuildDateBases(interaction.guild_id)
        await gdb.set_on_json('tickets', self.message_id, self.ticket_data)

        view = await TicketsItemView(interaction.guild, self.message_id)
        await interaction.response.edit_message(embed=view.embed, view=view)

    @nextcord.ui.button(label='Delete', style=nextcord.ButtonStyle.danger)
    async def delete(self, button: nextcord.Button, interaction: nextcord.Interaction):
        gdb = GuildDateBases(interaction.guild_id)
        tickets: TicketsPayload = await gdb.get('tickets', {})
        ticket_data = tickets.pop(self.message_id, None)

        channel = interaction.guild.get_channel(ticket_data['channel_id'])
        with contextlib.suppress(nextcord.NotFound, AttributeError):
            await channel.get_partial_message(self.message_id).delete()

        await delete_every_tickets(interaction.guild, self.message_id)

        await gdb.set('tickets', tickets)

        view = await tickets_view.TicketsView(interaction.guild)
        await interaction.response.edit_message(embed=view.embed, view=view)

    @nextcord.ui.button(label='Delete with channels', style=nextcord.ButtonStyle.danger)
    async def delete_with_chls(self, button: nextcord.Button, interaction: nextcord.Interaction):
        gdb = GuildDateBases(interaction.guild_id)
        tickets: TicketsPayload = await gdb.get('tickets', {})
        ticket_data = tickets.pop(self.message_id, None)

        channel = interaction.guild.get_channel(ticket_data['channel_id'])
        with contextlib.suppress(nextcord.NotFound, AttributeError):
            await channel.delete()

        if ticket_data.get('type', DEFAULT_TICKET_TYPE) == 1:
            channels = await delete_every_tickets(interaction.guild, self.message_id)
        else:
            channels = []

        channels.append(channel)

        category = interaction.guild.get_channel(
            ticket_data.get('category_id'))
        if len(set(category.channels)-set(channels)) == 0:
            await category.delete()

        if (
            channel.category
            and category != channel.category
            and len(set(category.channels)-set(channels)) == 0
        ):
            await channel.category.delete()

        await gdb.set('tickets', tickets)

        view = await tickets_view.TicketsView(interaction.guild)
        await interaction.response.edit_message(embed=view.embed, view=view)
