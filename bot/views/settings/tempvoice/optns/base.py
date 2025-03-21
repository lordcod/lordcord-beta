from abc import ABC
from typing import Optional
import nextcord

from bot.misc.plugins.tempvoice import TempVoiceModule
from bot.misc.utils import get_emoji_as_color
from bot.views.settings import tempvoice
from bot.views.settings._view import DefaultSettingsView


class OptionItem(ABC):
    label: str
    description: Optional[str] = None
    emoji: Optional[str] = None

    async def __init__(self, guild: nextcord.Guild):
        pass

    def get_emoji(self, system_emoji: int):
        if self.emoji is None:
            return None
        try:
            return get_emoji_as_color(system_emoji, self.emoji)
        except KeyError:
            return self.emoji

    async def edit_panel(self, interaction: nextcord.Interaction) -> None:
        await TempVoiceModule.edit_panel(interaction.guild)

    async def update(self, interaction: nextcord.Interaction) -> None:
        view = await tempvoice.TempVoiceView(interaction.guild)
        await interaction.response.edit_message(embed=view.embed, view=view)

    async def callback(self, interaction: nextcord.Interaction) -> None:
        await self.update(interaction)


class FunctionOptionItem(OptionItem):
    ...


class ViewOptionItem(DefaultSettingsView, OptionItem):
    embed: Optional[nextcord.Embed] = None

    @nextcord.ui.button(label='Back', style=nextcord.ButtonStyle.red)
    async def back(self,
                   button: nextcord.ui.Button,
                   interaction: nextcord.Interaction):
        await self.update(interaction)
