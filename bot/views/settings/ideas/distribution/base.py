from abc import ABC
from typing import Optional

import nextcord

from bot.databases.handlers.guildHD import GuildDateBases
from bot.databases.varstructs import IdeasPayload
from bot.misc.utils import get_emoji_as_color
from bot.views.settings import ideas
from bot.views.settings._view import DefaultSettingsView


class OptionItem(ABC):
    label: str
    description: Optional[str] = None
    emoji: Optional[str] = None

    async def __init__(self, guild: nextcord.Guild):
        self.guild = guild

    def get_emoji(self, system_emoji: int):
        if self.emoji is None:
            return None
        try:
            return get_emoji_as_color(system_emoji, self.emoji)
        except KeyError:
            return self.emoji

    async def get_ideas_data(self) -> IdeasPayload:
        gdb = GuildDateBases(self.guild.id)
        return await gdb.get('ideas')

    async def set_ideas_data(self, ideas_data: IdeasPayload) -> None:
        gdb = GuildDateBases(self.guild.id)
        await gdb.set('ideas', ideas_data)

    async def edit_ideas_service(self, key, value) -> None:
        gdb = GuildDateBases(self.guild.id)
        await gdb.set_on_json('ideas', key, value)

    async def update(self, interaction: nextcord.Interaction):
        view = await ideas.IdeasView(interaction.guild)
        await interaction.response.edit_message(embed=view.embed, view=view)

    async def callback(self, interaction: nextcord.Interaction) -> None:
        await self.update(interaction)


class ViewOptionItem(DefaultSettingsView, OptionItem):
    embed: Optional[nextcord.Embed] = None

    def edit_row_back(self, row: int) -> None:
        old_row = self.back._rendered_row
        self.back.row = row
        self.back._rendered_row = row
        if old_row is not None:
            weights = self._View__weights
            weights.weights[old_row] -= 1
            weights.weights[row] += 1

    @nextcord.ui.button(label='Back', style=nextcord.ButtonStyle.red)
    async def back(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await self.update(interaction)


class FunctionOptionItem(OptionItem):
    pass
