from __future__ import annotations

from typing import Optional
import nextcord
from bot.databases.varstructs import TicketsButtonsPayload
from bot.misc import tickettools
from bot.misc.utils import AsyncSterilization


@AsyncSterilization
class CloseTicketView(nextcord.ui.View):
    async def __init__(self, guild_id: Optional[int] = None, buttons: Optional[TicketsButtonsPayload] = None) -> None:
        super().__init__(timeout=None)
        if guild_id is None:
            return

        button = buttons.get('close_button')
        self.close_button.style = button.get('style')
        self.close_button.label = button.get('label')
        self.close_button.emoji = button.get('emoji')

    @nextcord.ui.button(custom_id="ticket:close")
    async def close_button(self,
                           button: nextcord.ui.Button,
                           interaction: nextcord.Interaction):
        await interaction.response.defer()
        ticket = await tickettools.ModuleTicket.from_channel_id(interaction.user, interaction.channel)
        await ticket.close()
