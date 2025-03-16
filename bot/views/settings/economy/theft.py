from typing import Optional
import nextcord
from bot.databases import GuildDateBases
from bot.languages import i18n
from bot.misc.utils import TimeCalculator, AsyncSterilization

from bot.resources.info import DEFAULT_ECONOMY_SETTINGS
from .. import economy
from .._view import DefaultSettingsView


@AsyncSterilization
class TheftView(DefaultSettingsView):
    embed: nextcord.Embed

    async def __init__(self, guild: nextcord.Guild, value: Optional[str] = None) -> None:
        self.value = value
        self.embed = (await economy.Economy(guild)).embed
        self.gdb = GuildDateBases(guild.id)
        locale = await self.gdb.get('language')

        super().__init__()

        if value:
            self.edit.disabled = False
            self.reset.disabled = False

        self.back.label = i18n.t(locale, 'settings.button.back')
        self.edit.label = i18n.t(locale, 'settings.button.edit')
        self.reset.label = i18n.t(locale, 'settings.button.edit')

    @nextcord.ui.button(label='Back', style=nextcord.ButtonStyle.red)
    async def back(self,
                   button: nextcord.ui.Button,
                   interaction: nextcord.Interaction):
        view = await economy.Economy(interaction.guild)
        await interaction.message.edit(embed=view.embed, view=view)

    @nextcord.ui.button(label='Edit', style=nextcord.ButtonStyle.success, disabled=True)
    async def edit(self,
                   button: nextcord.ui.Button,
                   interaction: nextcord.Interaction):
        return

    @nextcord.ui.button(label='Reset', style=nextcord.ButtonStyle.blurple, disabled=True)
    async def reset(self,
                    button: nextcord.ui.Button,
                    interaction: nextcord.Interaction):
        return
