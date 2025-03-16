import nextcord

from bot.languages import i18n
from bot.misc.utils import AsyncSterilization


from .modal import ModalBuilder
from .. import reactions
from .._view import DefaultSettingsView

from bot.databases import GuildDateBases


@AsyncSterilization
class ReactData(DefaultSettingsView):
    async def __init__(self, channel: nextcord.TextChannel, channel_data: dict) -> None:
        self.gdb = GuildDateBases(channel.guild.id)
        locale = await self.gdb.get('language')
        color = await self.gdb.get('color')
        self.forum_message = await self.gdb.get('reactions')

        self.channel_data = channel_data
        self.channel = channel

        self.embed = nextcord.Embed(
            title=i18n.t(locale, 'settings.reactions.init.brief'),
            description=i18n.t(locale, 'settings.reactions.init.description'),
            color=color
        )
        self.embed.add_field(
            name='',
            value=i18n.t(
                locale, 'settings.reactions.init.dddesc',
                channel=channel.mention,
                emojis=', '.join([emo for emo in channel_data])
            )
        )

        super().__init__()

        self.back.label = i18n.t(
            locale, 'settings.button.back')
        self.edit_reactions.label = i18n.t(
            locale, 'settings.reactions.button.edit')
        self.delete_reactions.label = i18n.t(
            locale, 'settings.reactions.button.delete')

    @nextcord.ui.button(label='Back', style=nextcord.ButtonStyle.red)
    async def back(self,
                   button: nextcord.ui.Button,
                   interaction: nextcord.Interaction):
        view = await reactions.AutoReactions(interaction.guild)
        await interaction.response.edit_message(embed=view.embed, view=view)

    @nextcord.ui.button(label='Edit reaction',
                        style=nextcord.ButtonStyle.primary)
    async def edit_reactions(self,
                             button: nextcord.ui.Button,
                             interaction: nextcord.Interaction):
        modal = await ModalBuilder(interaction.guild_id, self.channel.id)
        await interaction.response.send_modal(modal)

    @nextcord.ui.button(label='Delete reaction',
                        style=nextcord.ButtonStyle.red)
    async def delete_reactions(self,
                               button: nextcord.ui.Button,
                               interaction: nextcord.Interaction):
        channel_id = self.channel.id

        self.forum_message.pop(channel_id)
        await self.gdb.set('reactions', self.forum_message)

        view = await reactions.AutoReactions(interaction.guild)
        await interaction.response.edit_message(embed=view.embed, view=view)
