from typing import Optional
import nextcord

from bot.misc.utils import AsyncSterilization


from .modal import ModalBuilder
from .. import reactions
from .._view import DefaultSettingsView

from bot.databases import GuildDateBases
from bot.languages import i18n


@AsyncSterilization
class DropDownBuilder(nextcord.ui.ChannelSelect):
    async def __init__(self, guild_id) -> None:
        self.gdb = GuildDateBases(guild_id)
        locale = await self.gdb.get('language')

        super().__init__(
            placeholder=i18n.t(
                locale, 'settings.reactions.addres.placeholder'),
            channel_types=[nextcord.ChannelType.news,
                           nextcord.ChannelType.text]
        )

    async def callback(self, interaction: nextcord.Interaction) -> None:
        channel: nextcord.TextChannel = self.values[0]
        reacts: dict = await self.gdb.get('reactions')
        locale: str = await self.gdb.get('language')

        if channel.id in reacts:
            await interaction.response.send_message(i18n.t(
                locale, 'settings.reactions.addres.channel-error'),
                ephemeral=True)
            return

        view = await InstallEmojiView(channel.guild.id, channel.id)
        await interaction.response.edit_message(view=view)


@AsyncSterilization
class InstallEmojiView(DefaultSettingsView):
    embed:  nextcord.Embed

    async def __init__(self, guild_id: int, channel_id: Optional[int] = None) -> None:
        self.channel_id = channel_id
        gdb = GuildDateBases(guild_id)
        locale = await gdb.get('language')
        color = await gdb.get('color')

        self.embed = nextcord.Embed(
            title=i18n.t(locale, 'settings.reactions.init.title'),
            description=i18n.t(locale, 'settings.reactions.init.description'),
            color=color
        )
        # TODO LOCALIZATION
        self.embed.add_field(
            name='',
            value='> Select a channel and then click set reactions'
        )

        super().__init__()

        if channel_id is not None:
            self.install.disabled = False

        self.back.label = i18n.t(locale, 'settings.button.back')
        self.install.label = i18n.t(
            locale, 'settings.reactions.addres.install-emoji')

        DDB = await DropDownBuilder(guild_id)
        self.add_item(DDB)

    @nextcord.ui.button(label='Back',
                        style=nextcord.ButtonStyle.red)
    async def back(self,
                   button: nextcord.ui.Button,
                   interaction: nextcord.Interaction):
        view = await reactions.AutoReactions(interaction.guild)
        await interaction.response.edit_message(embed=view.embed, view=view)

    @nextcord.ui.button(label='Set emoji',
                        style=nextcord.ButtonStyle.blurple,
                        disabled=True)
    async def install(self,
                      button: nextcord.ui.Button,
                      interaction: nextcord.Interaction):
        modal = await ModalBuilder(interaction.guild_id, self.channel_id)
        await interaction.response.send_modal(modal)
