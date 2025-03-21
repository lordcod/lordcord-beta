from __future__ import annotations

import nextcord
from typing import TYPE_CHECKING, Optional

import nextcord.enums
from bot.databases.varstructs import TicketsButtonsPayload
from bot.misc.utils import AsyncSterilization

if TYPE_CHECKING:
    from bot.misc.plugins.tickettools import ModuleTicket


@AsyncSterilization
class TicketsModal(nextcord.ui.Modal):
    async def __init__(
        self,
        ticket: ModuleTicket,
        buttons: Optional[TicketsButtonsPayload] = None
    ) -> None:
        self.ticket = ticket
        ticket_data = await ticket.fetch_guild_ticket()
        placeholder = buttons.get('modal_placeholder')

        if ticket.selected_category and ticket.selected_category.get('modals'):
            modals = ticket.selected_category.get('modals')
        else:
            modals = ticket_data.get('modals')

        super().__init__(placeholder)

        for tip in modals:
            style = nextcord.enums.try_enum(nextcord.TextInputStyle,
                                            tip.get('style', 1))
            min_lenght = tip.get('min_lenght') or 0
            max_lenght = tip.get('max_lenght') or 4000
            inp = nextcord.ui.TextInput(
                label=tip.get('label'),
                style=style,
                min_length=min_lenght,
                max_length=max_lenght,
                required=tip.get('required'),
                default_value=tip.get('default_value'),
                placeholder=tip.get('placeholder'),
            )
            self.add_item(inp)

    async def callback(self, interaction: nextcord.Interaction):
        items = {inp.label: inp.value for inp in self.children}
        await self.ticket.create_after_modals(interaction, items)
