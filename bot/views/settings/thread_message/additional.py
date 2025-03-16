import nextcord

from bot.languages import i18n
from bot.misc.utils import AsyncSterilization


from .modal import ModalBuilder
from .. import thread_message
from .._view import DefaultSettingsView

from bot.databases import GuildDateBases


@AsyncSterilization
class ChannelDropDown(nextcord.ui.ChannelSelect):
    async def __init__(self, guild_id) -> None:
        self.gdb = GuildDateBases(guild_id)
        locale = await self.gdb.get('language')
        super().__init__(
            placeholder=i18n.t(
                locale, 'settings.thread.addptional.placeholder'),
            channel_types=[nextcord.ChannelType.forum,
                           nextcord.ChannelType.text]
        )

    async def callback(self, interaction: nextcord.Interaction) -> None:
        channel: nextcord.TextChannel = self.values[0]
        locale = await self.gdb.get('language')
        forum_message = await self.gdb.get('thread_messages')

        if channel.id in forum_message:
            await interaction.response.send_message(i18n.t(
                locale, 'settings.thread.addptional.channel-error'))
            return

        view = await InstallThreadView(channel.guild.id, channel.id)
        view.install.disabled = False
        await interaction.response.edit_message(view=view)


@AsyncSterilization
class InstallThreadView(DefaultSettingsView):
    async def __init__(self, guild_id, installer=None) -> None:
        gdb = GuildDateBases(guild_id)
        locale = await gdb.get('language')
        self.installer = installer

        super().__init__()

        self.back.label = i18n.t(
            locale, 'settings.button.back')
        self.install.label = i18n.t(
            locale, 'settings.thread.addptional.button.install-mes')

        DDB = await ChannelDropDown(guild_id)

        self.add_item(DDB)

    @nextcord.ui.button(label='Back', style=nextcord.ButtonStyle.red)
    async def back(self,
                   button: nextcord.ui.Button,
                   interaction: nextcord.Interaction):
        view = await thread_message.AutoThreadMessage(interaction.guild)

        await interaction.response.edit_message(embed=view.embed, view=view)

    @nextcord.ui.button(label='Install message',
                        style=nextcord.ButtonStyle.blurple,
                        disabled=True)
    async def install(self,
                      button: nextcord.ui.Button,
                      interaction: nextcord.Interaction):
        modal = await ModalBuilder(interaction.guild_id, self.installer)

        await interaction.response.send_modal(modal)
