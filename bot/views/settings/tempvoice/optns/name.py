import nextcord

from bot.databases.handlers.guildHD import GuildDateBases
from bot.languages import i18n
from bot.misc.utils import AsyncSterilization
from bot.views.settings.tempvoice.optns.base import OptionItem


@AsyncSterilization
class NameModal(nextcord.ui.Modal, OptionItem):
    label = 'settings.tempvoice.name.label'
    description = 'settings.tempvoice.name.description'
    emoji = 'name'

    async def __init__(self, guild: nextcord.Guild):
        gdb = GuildDateBases(guild.id)
        locale = await gdb.get('language')
        data = await gdb.get('tempvoice')
        name = data.get('name', '{voice.count.active}-{member.username}')

        super().__init__(i18n.t(locale, 'settings.tempvoice.brief_title'))

        self.name = nextcord.ui.TextInput(
            label=i18n.t(locale, 'settings.tempvoice.name.label'),
            placeholder=name
        )
        self.add_item(self.name)

    async def callback(self, interaction: nextcord.Interaction) -> None:
        gdb = GuildDateBases(interaction.guild_id)
        name = self.name.value
        await gdb.set_on_json('tempvoice', 'channel_name', name)

        await self.update(interaction)
