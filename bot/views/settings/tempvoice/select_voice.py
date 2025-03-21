from typing import Optional
import nextcord

from bot.misc.plugins.tempvoice import TempVoiceModule
from bot.misc.utils import AsyncSterilization


from .._view import DefaultSettingsView

from bot.databases import GuildDateBases
from .. import tempvoice
from bot.languages import i18n


@AsyncSterilization
class TempVoiceSelectorChannelDropDown(nextcord.ui.ChannelSelect):
    async def __init__(
        self,
        guild: nextcord.Guild,
        selected_channel: Optional[nextcord.VoiceChannel] = None,
        selected_channel_panel: Optional[nextcord.TextChannel] = None,
        selected_category: Optional[nextcord.CategoryChannel] = None,
    ) -> None:
        gdb = GuildDateBases(guild.id)
        locale = await gdb.get('language')

        self.selected_channel = selected_channel
        self.selected_channel_panel = selected_channel_panel
        self.selected_category = selected_category

        super().__init__(placeholder=i18n.t(locale, 'settings.tempvoice.select.channel'),
                         channel_types=[nextcord.ChannelType.voice])

    async def callback(self, interaction: nextcord.Interaction) -> None:
        channel = self.values[0]
        view = await TempVoiceSelectorView(
            interaction.guild,
            channel,
            self.selected_channel_panel,
            self.selected_category
        )
        await interaction.response.edit_message(embed=view.embed, view=view)


@AsyncSterilization
class TempVoiceSelectorChannelPanelDropDown(nextcord.ui.ChannelSelect):
    async def __init__(
        self,
        guild: nextcord.Guild,
        selected_channel: Optional[nextcord.VoiceChannel] = None,
        selected_channel_panel: Optional[nextcord.TextChannel] = None,
        selected_category: Optional[nextcord.CategoryChannel] = None,
    ) -> None:
        gdb = GuildDateBases(guild.id)
        locale = await gdb.get('language')

        self.selected_channel = selected_channel
        self.selected_channel_panel = selected_channel_panel
        self.selected_category = selected_category

        super().__init__(placeholder=i18n.t(locale, 'settings.tempvoice.select.panel'),
                         channel_types=[nextcord.ChannelType.text, nextcord.ChannelType.news])

    async def callback(self, interaction: nextcord.Interaction) -> None:
        channel = self.values[0]
        view = await TempVoiceSelectorView(
            interaction.guild,
            self.selected_channel,
            channel,
            self.selected_category
        )
        await interaction.response.edit_message(embed=view.embed, view=view)


@AsyncSterilization
class TempVoiceSelectorCategoryDropDown(nextcord.ui.ChannelSelect):
    async def __init__(
        self,
        guild: nextcord.Guild,
        selected_channel: Optional[nextcord.VoiceChannel] = None,
        selected_channel_panel: Optional[nextcord.TextChannel] = None,
        selected_category: Optional[nextcord.CategoryChannel] = None,
    ) -> None:
        gdb = GuildDateBases(guild.id)
        locale = await gdb.get('language')

        self.selected_channel = selected_channel
        self.selected_channel_panel = selected_channel_panel
        self.selected_category = selected_category

        super().__init__(placeholder=i18n.t(locale, 'settings.tempvoice.select.category'),
                         channel_types=[nextcord.ChannelType.category])

    async def callback(self, interaction: nextcord.Interaction) -> None:
        category = self.values[0]
        view = await TempVoiceSelectorView(
            interaction.guild,
            self.selected_channel,
            self.selected_channel_panel,
            category
        )
        await interaction.response.edit_message(embed=view.embed, view=view)


@AsyncSterilization
class TempVoiceSelectorView(DefaultSettingsView):
    embed: nextcord.Embed = None

    async def __init__(
        self,
        guild: nextcord.Guild,
        selected_channel: Optional[nextcord.VoiceChannel] = None,
        selected_channel_panel: Optional[nextcord.TextChannel] = None,
        selected_category: Optional[nextcord.CategoryChannel] = None,
    ) -> None:
        gdb = GuildDateBases(guild.id)
        locale = await gdb.get('language')

        self.selected_channel = selected_channel
        self.selected_channel_panel = selected_channel_panel
        self.selected_category = selected_category

        gdb = GuildDateBases(guild.id)
        locale = await gdb.get('language')

        super().__init__()

        if selected_channel is not None:
            self.create.disabled = False

        self.add_item(await TempVoiceSelectorChannelDropDown(guild, selected_channel,
                                                             selected_channel_panel, selected_category))
        self.add_item(await TempVoiceSelectorChannelPanelDropDown(guild, selected_channel,
                                                                  selected_channel_panel,
                                                                  selected_category))
        self.add_item(await TempVoiceSelectorCategoryDropDown(guild, selected_channel,
                                                              selected_channel_panel,
                                                              selected_category))

        self.back.label = i18n.t(locale, 'settings.button.back')
        self.create.label = i18n.t(locale, 'settings.button.create')

    @nextcord.ui.button(label='Back', style=nextcord.ButtonStyle.red)
    async def back(self,
                   button: nextcord.ui.Button,
                   interaction: nextcord.Interaction):
        view = await tempvoice.TempVoiceView(interaction.user)
        await interaction.response.edit_message(embed=view.embed, view=view)

    @nextcord.ui.button(label='Create', style=nextcord.ButtonStyle.blurple, disabled=True)
    async def create(self,
                     button: nextcord.ui.Button,
                     interaction: nextcord.Interaction):
        gdb = GuildDateBases(interaction.guild_id)

        if self.selected_category is not None:
            category_id = self.selected_category.id
        elif self.selected_channel.category is not None:
            category_id = self.selected_channel.category.id
        else:
            category_id = None

        if self.selected_channel_panel:
            type_message_panel = 1
            panel_channel_id = self.selected_channel_panel.id
        else:
            type_message_panel = 2
            panel_channel_id = None

        data = {
            'enabled': True,
            'channel_id': self.selected_channel.id,
            'category_id': category_id,
            'panel_channel_id': panel_channel_id,
            'type_message_panel': type_message_panel
        }

        await gdb.set('tempvoice', data)
        await TempVoiceModule.create_panel(interaction.guild)

        view = await tempvoice.TempVoiceView(interaction.guild)
        await interaction.response.edit_message(embed=view.embed, view=view)
