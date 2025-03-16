import nextcord

from bot.databases.handlers.guildHD import GuildDateBases
from bot.databases.varstructs import TicketsPayload
from bot.misc.utils import AsyncSterilization
from .base import FunctionOptionItem


@AsyncSterilization
class ClosedUserFunction(FunctionOptionItem):
    label: str
    description: str

    async def __init__(self, guild: nextcord.Guild, message_id: int):
        self.message_id = message_id

        gdb = GuildDateBases(guild.id)
        tickets: TicketsPayload = await gdb.get('tickets')
        ticket_data = tickets[message_id]
        self.closed_user = ticket_data.get('user_closed', True)

        if self.closed_user:
            self.label = 'settings.tickets.closed_user.label.disable'
            self.description = 'settings.tickets.closed_user.description.disable'
            self.emoji = 'ticlose'
        else:
            self.label = 'settings.tickets.closed_user.label.enable'
            self.description = 'settings.tickets.closed_user.description.enable'
            self.emoji = 'ticopen'

    async def callback(self, interaction: nextcord.Interaction) -> None:
        gdb = GuildDateBases(interaction.guild.id)
        tickets: TicketsPayload = await gdb.get('tickets')
        ticket_data = tickets[self.message_id]
        ticket_data['user_closed'] = not self.closed_user
        await gdb.set_on_json('tickets', self.message_id, ticket_data)

        await self.update(interaction)
