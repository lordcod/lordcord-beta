from typing import Dict, List
import nextcord

from bot.databases.handlers.guildHD import GuildDateBases
from bot.languages import i18n
from bot.misc.utils import AsyncSterilization
from bot.views.settings import tempvoice
from bot.views.settings.tempvoice.optns.panel_type import TypePanelView
from .optns.base import FunctionOptionItem, OptionItem, ViewOptionItem
from .optns.limit import LimitModal
from .optns.name import NameModal

distribution: List[AsyncSterilization[OptionItem]] = [
    LimitModal, NameModal, TypePanelView]
distribution_keys: Dict[str, AsyncSterilization[OptionItem]] = {
    item.cls.__name__.lower(): item for item in distribution}


@AsyncSterilization
class TempVoiceDropDown(nextcord.ui.StringSelect):
    async def __init__(self, guild: nextcord.Guild):
        gdb = GuildDateBases(guild.id)
        locale = await gdb.get('language')
        system_emoji = await gdb.get('system_emoji')

        self.items = {key: await item(guild) for key, item in distribution_keys.items()}
        super().__init__(
            placeholder=i18n.t(locale, 'settings.tempvoice.select.opts'),
            options=[
                nextcord.SelectOption(
                    label=i18n.t(locale, item.label),
                    value=key,
                    description=i18n.t(locale, item.description),
                    emoji=item.get_emoji(system_emoji)
                )
                for key, item in self.items.items()
            ])

    async def callback(self, interaction: nextcord.Interaction) -> None:
        value = self.values[0]
        item = self.items[value]

        if isinstance(item, nextcord.ui.Modal):
            await interaction.response.send_modal(item)

            view = await tempvoice.TempVoiceView(interaction.guild)
            await interaction.message.edit(embed=view.embed, view=view)
        elif isinstance(item, ViewOptionItem):
            await interaction.response.edit_message(embed=item.embed, view=item)
        elif isinstance(item, FunctionOptionItem):
            await item.callback(interaction)
