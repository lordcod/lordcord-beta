from abc import ABC

from typing import Any, Optional, overload
import nextcord
from bot.databases.handlers.guildHD import GuildDateBases
from bot.databases.varstructs import TicketsItemPayload, TicketsPayload
from bot.misc.plugins.tickettools import ModuleTicket
from bot.misc.utils import AsyncSterilization, get_emoji_as_color
from bot.views.settings._view import DefaultSettingsView
from bot.views.settings.tickets.item import view as item_view
from bot.views.settings.tickets.item.embeds import get_embed


class OptionItem(ABC):
    label: str
    description: Optional[str] = None
    emoji: Optional[str] = None

    message_id: int

    async def __init__(self, guild: nextcord.Guild, message_id: int):
        self.guild = guild
        self.message_id = message_id

    def get_emoji(self, system_emoji: int):
        if self.emoji is None:
            return None
        try:
            return get_emoji_as_color(system_emoji, self.emoji)
        except KeyError:
            return self.emoji

    async def get_ticket_data(self, guild: Optional[nextcord.Guild] = None) -> TicketsItemPayload:
        guild = guild or getattr(self, 'guild', None)
        gdb = GuildDateBases(guild.id)
        tickets: TicketsPayload = await gdb.get('tickets', {})
        ticket_data = tickets[self.message_id]
        return ticket_data

    @overload
    async def edit_ticket_data(
        self, guild: nextcord.Guild, ticket_data: TicketsItemPayload) -> None: ...

    @overload
    async def edit_ticket_data(
        self, ticket_data: TicketsItemPayload) -> None: ...

    async def edit_ticket_data(self, *args) -> None:
        if len(args) == 1:
            guild = self.guild
            ticket_data = args[0]
        elif len(args) == 2:
            guild = args[0]
            ticket_data = args[1]
        else:
            assert False, "no more than 2 arguments are allowed"

        gdb = GuildDateBases(guild.id)
        await gdb.set_on_json('tickets', self.message_id, ticket_data)

    async def get_ticket_data_key(self, guild: nextcord.Guild, key: str, default: Any = None) -> None:
        ticket_data = await self.get_ticket_data(guild)
        return ticket_data.get(key, default)

    async def edit_ticket_data_key(self, guild: nextcord.Guild, key: str, value: Any) -> None:
        gdb = GuildDateBases(guild.id)
        tickets: TicketsPayload = await gdb.get('tickets', {})
        ticket_data = tickets[self.message_id]

        ticket_data[key] = value

        await gdb.set_on_json('tickets', self.message_id, ticket_data)

    async def edit_panel(self, interaction: nextcord.Interaction) -> None:
        await ModuleTicket.update_ticket_panel(interaction.guild, self.message_id)

    async def update(self, interaction: nextcord.Interaction) -> None:
        view = await item_view.TicketsItemView(interaction.guild, self.message_id)
        await interaction.response.edit_message(embed=view.embed, view=view)

    async def callback(self, interaction: nextcord.Interaction) -> None:
        await self.update(interaction)


class FunctionOptionItem(OptionItem):
    async def render_label(self, guild: nextcord.Guild, message_id: int):
        pass


class ViewOptionItem(DefaultSettingsView, OptionItem):
    embed: Optional[nextcord.Embed] = None

    def __init__(
        self,
        *,
        timeout: Optional[float] = 180,
        auto_defer: bool = True,
        prevent_update: bool = True
    ) -> None:
        super().__init__(timeout=timeout, auto_defer=auto_defer, prevent_update=prevent_update)

    def edit_row_back(self, row: int) -> None:
        old_row = self.back._rendered_row
        self.back.row = row
        self.back._rendered_row = row
        if old_row is not None:
            weights = self._View__weights
            weights.weights[old_row] -= 1
            weights.weights[row] += 1

    @nextcord.ui.button(label='Back', style=nextcord.ButtonStyle.red)
    async def back(self,
                   button: nextcord.ui.Button,
                   interaction: nextcord.Interaction):
        view = await item_view.TicketsItemView(interaction.guild, self.message_id)
        await interaction.response.edit_message(embed=view.embed, view=view)

    async def get_embed(self, guild: nextcord.Guild) -> nextcord.Embed:
        if self.embed is None:
            embed = await get_embed(guild, self.message_id)
        else:
            embed = self.embed
        return embed

    async def update(self, interaction: nextcord.Interaction) -> None:
        view = await AsyncSterilization(type(self))(interaction.guild, self.message_id)
        embed = await self.get_embed(interaction.guild)
        await interaction.response.edit_message(embed=embed, view=view)
