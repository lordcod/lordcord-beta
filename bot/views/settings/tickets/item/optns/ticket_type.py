import nextcord

from bot.databases.handlers.guildHD import GuildDateBases
from bot.databases.varstructs import TicketsPayload
from bot.languages import i18n
from bot.misc.utils import AsyncSterilization
from bot.resources.info import DEFAULT_TICKET_TYPE
from .base import ViewOptionItem


@AsyncSterilization
class TypeTicketDropDown(nextcord.ui.StringSelect['TicketTypeView']):
    async def __init__(self, guild_id: int, ticket_type: int) -> None:
        gdb = GuildDateBases(guild_id)
        locale = await gdb.get('language')

        options = [
            nextcord.SelectOption(
                label=i18n.t(
                    locale, 'settings.tickets.type.dropdown.channel.label'),
                description=i18n.t(
                    locale, 'settings.tickets.type.dropdown.channel.description'),
                value=1,
                default=ticket_type == 1
            ),
            nextcord.SelectOption(
                label=i18n.t(
                    locale, 'settings.tickets.type.dropdown.thread.label'),
                description=i18n.t(
                    locale, 'settings.tickets.type.dropdown.thread.description'),
                value=2,
                default=ticket_type == 2
            ),
        ]
        super().__init__(options=options)

    async def callback(self, interaction: nextcord.Interaction) -> None:
        value = int(self.values[0])

        gdb = GuildDateBases(interaction.guild_id)
        tickets_data: TicketsPayload = await gdb.get('tickets')
        data = tickets_data[self.view.message_id]
        data['type'] = value
        await gdb.set_on_json('tickets', self.view.message_id, data)

        await self.view.update(interaction)


@AsyncSterilization
class TicketTypeView(ViewOptionItem):
    label = 'settings.tickets.type.label'
    description = 'settings.tickets.type.description'
    emoji = 'tictype'

    async def __init__(self, guild: nextcord.Guild, message_id: int):
        self.message_id = message_id

        gdb = GuildDateBases(guild.id)
        tickets_data: TicketsPayload = await gdb.get('tickets')
        data = tickets_data[message_id]
        ticket_type = data.get('type', DEFAULT_TICKET_TYPE)

        super().__init__()

        ttdd = await TypeTicketDropDown(guild.id, ticket_type)
        self.add_item(ttdd)
