import nextcord

from bot.languages import i18n
from bot.misc.utils import AsyncSterilization


from .. import thread_message

from bot.databases import GuildDateBases


@AsyncSterilization
class ModalBuilder(nextcord.ui.Modal):
    async def __init__(self, guild_id, channel_id) -> None:
        gdb = GuildDateBases(guild_id)
        locale = await gdb.get('language')
        self.channel_id = channel_id
        super().__init__(i18n.t(
            locale, 'settings.thread.modal.title'))

        self.content = nextcord.ui.TextInput(
            label=i18n.t(
                locale, 'settings.thread.modal.label'),
            placeholder=i18n.t(
                locale, 'settings.thread.modal.placeholder'),
            style=nextcord.TextInputStyle.paragraph
        )

        self.add_item(self.content)

    async def callback(self, interaction: nextcord.Interaction) -> None:
        gdb = GuildDateBases(interaction.guild_id)
        forum_message = await gdb.get('thread_messages')

        content = self.content.value
        channel_id = self.channel_id

        forum_message[channel_id] = content

        await gdb.set('thread_messages', forum_message)

        view = await thread_message.AutoThreadMessage(interaction.guild)
        await interaction.response.edit_message(embed=view.embed, view=view)
