import nextcord

from bot.databases.handlers.guildHD import GuildDateBases
from bot.languages import i18n
from bot.misc.utils import AsyncSterilization
from .base import OptionItem


@AsyncSterilization
class LimitModal(nextcord.ui.Modal, OptionItem):
    label = 'settings.tempvoice.limit.label'
    description = 'settings.tempvoice.limit.description'
    emoji = 'limit'

    async def __init__(self, guild: nextcord.Guild):
        gdb = GuildDateBases(guild.id)
        data = await gdb.get('tempvoice')
        locale = await gdb.get('language')
        limit = data.get('limit', 4)

        super().__init__(i18n.t(locale, 'settings.tempvoice.brief_title'))

        self.limit = nextcord.ui.TextInput(
            label=i18n.t(locale, 'settings.tempvoice.limit.label'),
            default_value=limit
        )
        self.add_item(self.limit)

    async def callback(self, interaction: nextcord.Interaction) -> None:
        gdb = GuildDateBases(interaction.guild_id)
        limit = self.limit.value
        await gdb.set_on_json('tempvoice', 'channel_limit', limit)

        await self.update(interaction)
