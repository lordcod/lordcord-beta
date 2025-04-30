import random
import string
from typing import Optional
import nextcord

from bot.databases.handlers.guildHD import GuildDateBases
from bot.languages import i18n
from bot.misc.lordbot import LordBot
from bot.misc.utils import AsyncSterilization, generate_message, get_payload, lord_format
from bot.views.information_dd import get_info_dd
from bot.views.settings import notification
from bot.views.settings._view import DefaultSettingsView


def generate_hex(): return ''.join(
    [random.choice(string.hexdigits) for _ in range(18)])


@AsyncSterilization
class FarewellMessageModal(nextcord.ui.Modal):
    embed = None

    async def __init__(self, guild: nextcord.Guild, data: dict):
        gdb = GuildDateBases(guild.id)
        locale = await gdb.get('language')

        self.data = data

        super().__init__(i18n.t(locale, 'settings.notifi.farewell.title'))

        self.message = nextcord.ui.TextInput(
            label=i18n.t(locale, 'settings.notifi.message.title'),
            placeholder=i18n.t(locale, 'settings.notifi.message.placeholder'),
            style=nextcord.TextInputStyle.paragraph,
            default_value=data.get('message')
        )
        self.add_item(self.message)

    async def callback(self, interaction: nextcord.Interaction[LordBot]) -> None:
        message = self.message.value
        self.data['message'] = message

        view = await FarewellView(interaction.guild,  self.data)
        await interaction.response.edit_message(embed=view.embed, view=view)


@AsyncSterilization
class FarewellChannelDropDown(nextcord.ui.ChannelSelect):
    async def __init__(self, guild: nextcord.Guild, data: dict):
        gdb = GuildDateBases(guild.id)
        locale = await gdb.get('language')

        self.data = data

        super().__init__(placeholder=i18n.t(locale, 'settings.notifi.dropdown.channel'),
                         channel_types=[nextcord.ChannelType.text, nextcord.ChannelType.news])

    async def callback(self, interaction: nextcord.Interaction) -> None:
        channel = self.values[0]
        self.data['channel_id'] = channel.id

        view = await FarewellView(interaction.guild,  self.data)
        await interaction.response.edit_message(embed=view.embed, view=view)


@AsyncSterilization
class FarewellView(DefaultSettingsView):
    embed = None

    async def __init__(self, guild: nextcord.Guild, data: Optional[dict] = None):
        gdb = GuildDateBases(guild.id)
        locale = await gdb.get('language')
        color = await gdb.get('color')
        farewell_data = await gdb.get('farewell_message', {})

        self.embed = nextcord.Embed(
            title=i18n.t(locale, 'settings.notifi.farewell.title'),
            color=color,
            description=i18n.t(locale, 'settings.notifi.farewell.description')
        )

        self.data = data
        if data is None:
            self.data = farewell_data

        super().__init__()

        if farewell_data:
            self.delete.disabled = False
        if self.data and 'message' in self.data and 'channel_id' in self.data:
            self.edit.disabled = False
        if self.data and 'message' in self.data:
            self.view_message.disabled = False
        if self.data and 'channel_id' in self.data:
            channel_name = guild.get_channel(self.data['channel_id']).name
        else:
            channel_name = i18n.t(locale, 'settings.notifi.unspecified')

        self.add_item(get_info_dd(
            placeholder=i18n.t(locale, 'settings.notifi.dropdown.info_channel',
                               channel=channel_name)
        ))
        self.add_item(await FarewellChannelDropDown(guild, self.data))

        self.back.label = i18n.t(locale, 'settings.button.back')
        self.save.label = i18n.t(locale, 'settings.button.save_changes')
        self.delete.label = i18n.t(locale, 'settings.button.delete')
        self.view_message.label = i18n.t(
            locale, 'settings.button.preview_message')
        self.change_message.label = i18n.t(
            locale, 'settings.button.change_message')

    @nextcord.ui.button(label='Back', style=nextcord.ButtonStyle.red, row=0)
    async def back(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        view = await notification.NotificationView(interaction.guild)
        await interaction.response.edit_message(embed=view.embed, view=view)

    @nextcord.ui.button(label='Save changes', style=nextcord.ButtonStyle.green, row=0, disabled=True)
    async def save(self, button: nextcord.ui.Button, interaction: nextcord.Interaction[LordBot]):
        gdb = GuildDateBases(interaction.guild_id)
        await gdb.set('farewell_message', self.data)

        view = await FarewellView(interaction.guild)
        await interaction.response.edit_message(embed=view.embed, view=view)

    @nextcord.ui.button(label='Delete', style=nextcord.ButtonStyle.red, row=0, disabled=True)
    async def delete(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        gdb = GuildDateBases(interaction.guild_id)
        await gdb.set('farewell_message', {})

        view = await FarewellView(interaction.guild)
        await interaction.response.edit_message(embed=view.embed, view=view)

    @nextcord.ui.button(label='Preview message', style=nextcord.ButtonStyle.success, row=1, disabled=True)
    async def view_message(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        message = self.data.get('message')

        payload = get_payload(member=interaction.user)

        message_format = lord_format(message, payload)
        data = generate_message(message_format)
        await interaction.response.send_message(**data, ephemeral=True)

    @nextcord.ui.button(label='Change message', style=nextcord.ButtonStyle.blurple, row=1)
    async def change_message(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        modal = await FarewellMessageModal(interaction.guild,  self.data)
        await interaction.response.send_modal(modal)
