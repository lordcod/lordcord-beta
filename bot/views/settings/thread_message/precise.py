import nextcord


from .modal import ModalBuilder
from .. import thread_message
from .._view import DefaultSettingsView

from bot.misc import utils
from bot.languages import i18n
from bot.databases import GuildDateBases


@utils.AsyncSterilization
class ThreadData(DefaultSettingsView):
    async def __init__(self, channel: nextcord.abc.GuildChannel, channel_data) -> None:
        self.channel_data = channel_data
        self.channel = channel

        self.gdb = GuildDateBases(channel.guild.id)
        self.forum_message = await self.gdb.get('thread_messages')
        locale = await self.gdb.get('language')

        super().__init__()

        self.back.label = i18n.t(
            locale, 'settings.button.back')
        self.message.label = i18n.t(
            locale, 'settings.thread.thread.button.view')
        self.edit_message.label = i18n.t(
            locale, 'settings.thread.thread.button.edit')
        self.delete_message.label = i18n.t(
            locale, 'settings.thread.thread.button.delete')

    @nextcord.ui.button(label='Back', style=nextcord.ButtonStyle.red)
    async def back(self,
                   button: nextcord.ui.Button,
                   interaction: nextcord.Interaction):
        view = await thread_message.AutoThreadMessage(interaction.guild)

        await interaction.response.edit_message(embed=view.embed, view=view)

    @nextcord.ui.button(label='Message', style=nextcord.ButtonStyle.success)
    async def message(self,
                      button: nextcord.ui.Button,
                      interaction: nextcord.Interaction):
        channel_content = self.channel_data

        gdb = GuildDateBases(interaction.guild_id)
        locale = await gdb.get('language')

        if not channel_content:
            await interaction.response.send_message(i18n.t(
                locale, 'settings.thread.thread.mes-not-found'))

        content = utils.generate_message(channel_content)
        await interaction.response.send_message(**content, ephemeral=True)

    @nextcord.ui.button(label='Edit message',
                        style=nextcord.ButtonStyle.primary)
    async def edit_message(self,
                           button: nextcord.ui.Button,
                           interaction: nextcord.Interaction):
        modal = await ModalBuilder(interaction.guild_id, self.channel.id)

        await interaction.response.send_modal(modal)

    @nextcord.ui.button(label='Delete message', style=nextcord.ButtonStyle.red)
    async def delete_message(self,
                             button: nextcord.ui.Button,
                             interaction: nextcord.Interaction):
        channel_id = self.channel.id
        self.forum_message.pop(channel_id, None)

        await self.gdb.set('thread_messages', self.forum_message)

        view = thread_message.AutoThreadMessage(interaction.guild)
        await interaction.response.edit_message(embed=view.embed, view=view)
