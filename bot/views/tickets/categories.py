from __future__ import annotations

import nextcord
from typing import TYPE_CHECKING
from bot.databases.varstructs import TicketsButtonsPayload
from bot.misc.utils import AsyncSterilization

if TYPE_CHECKING:
    from bot.misc.tickettools import ModuleTicket


@AsyncSterilization
class CategoryDropDown(nextcord.ui.StringSelect):
    async def __init__(self, ticket: ModuleTicket, buttons: TicketsButtonsPayload):
        self.ticket = ticket
        ticket_data = await ticket.fetch_guild_ticket()
        categories_data = ticket_data.get('categories')
        options = [
            nextcord.SelectOption(
                label=cat['label'],
                value=i,
                description=cat.get('description'),
                emoji=cat.get('emoji'),
            )
            for i, cat in enumerate(categories_data)
        ]
        placeholder = buttons.get('category_placeholder')
        super().__init__(
            placeholder=placeholder,
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: nextcord.Interaction) -> None:
        ticket_data = await self.ticket.fetch_guild_ticket()
        categories_data = ticket_data.get('categories')
        value = categories_data[int(self.values[0])]
        await self.ticket.create_after_category(interaction, value)


@AsyncSterilization
class CategoryView(nextcord.ui.View):
    async def __init__(self, ticket: ModuleTicket, buttons: TicketsButtonsPayload):
        super().__init__(timeout=300)
        self.add_item(await CategoryDropDown(ticket, buttons))
