from __future__ import annotations

from typing import TYPE_CHECKING, Optional
import nextcord
from bot.databases.varstructs import TicketsButtonsPayload
from bot.misc import tickettools
from bot.misc.utils import AsyncSterilization

if TYPE_CHECKING:
    from bot.misc.tickettools import ModuleTicket


@AsyncSterilization
class ControllerTicketView(nextcord.ui.View):
    async def __init__(self, guild_id: Optional[int] = None, buttons: Optional[TicketsButtonsPayload] = None) -> None:
        super().__init__(timeout=None)
        if guild_id is None:
            return

        delete_button = buttons.get('delete_button')
        self.delete_button.style = delete_button.get('style')
        self.delete_button.label = delete_button.get('label')
        self.delete_button.emoji = delete_button.get('emoji')

        reopen_button = buttons.get('reopen_button')
        self.reopen_button.style = reopen_button.get('style')
        self.reopen_button.label = reopen_button.get('label')
        self.reopen_button.emoji = reopen_button.get('emoji')

    @nextcord.ui.button(custom_id="ticket:delete")
    async def delete_button(self,
                            button: nextcord.ui.Button,
                            interaction: nextcord.Interaction):
        await interaction.response.defer()
        ticket = await tickettools.ModuleTicket.from_channel_id(interaction.user, interaction.channel)
        await ticket.delete()

    @nextcord.ui.button(custom_id="ticket:reopen")
    async def reopen_button(self,
                            button: nextcord.ui.Button,
                            interaction: nextcord.Interaction):
        await interaction.response.defer()
        ticket = await tickettools.ModuleTicket.from_channel_id(interaction.user, interaction.channel)
        await ticket.reopen(interaction.message)
