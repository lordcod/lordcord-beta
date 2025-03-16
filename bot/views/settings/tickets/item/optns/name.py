import nextcord

from bot.databases.handlers.guildHD import GuildDateBases
from bot.databases.varstructs import TicketsPayload
from bot.languages import i18n
from bot.misc.utils import AsyncSterilization
from .base import OptionItem


@AsyncSterilization
class TicketNameModal(nextcord.ui.Modal, OptionItem):
    label = 'settings.tickets.name.label'
    description = 'settings.tickets.name.description'
    emoji = 'ticname'

    async def __init__(self, guild: nextcord.Guild, message_id: int):
        self.message_id = message_id

        gdb = GuildDateBases(guild.id)
        locale = await gdb.get('language')
        tickets: TicketsPayload = await gdb.get('tickets')
        ticket_data = tickets[message_id]
        name = ticket_data.get('names').get('open')

        super().__init__(i18n.t(locale, 'settings.tickets.name.modal.title'))

        self.name = nextcord.ui.TextInput(
            label=i18n.t(locale, 'settings.tickets.name.modal.label'),
            placeholder=name,
            max_length=128
        )
        self.add_item(self.name)

    async def callback(self, interaction: nextcord.Interaction) -> None:
        gdb = GuildDateBases(interaction.guild_id)
        tickets: TicketsPayload = await gdb.get('tickets')
        ticket_data = tickets[self.message_id]

        name = self.name.value
        ticket_data['names']['open'] = name

        await gdb.set_on_json('tickets', self.message_id, ticket_data)

        await self.update(interaction)
