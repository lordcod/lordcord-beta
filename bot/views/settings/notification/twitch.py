import random
import re
import string
from typing import Optional
import nextcord

from bot.databases.handlers.guildHD import GuildDateBases
from bot.languages import i18n
from bot.misc.lordbot import LordBot
from bot.misc.utils import AsyncSterilization, generate_message
from bot.resources.info import DEFAULT_TWITCH_MESSAGE
from bot.views.settings import notification
from bot.views.settings._view import DefaultSettingsView


def generate_hex(): return ''.join(
    [random.choice(string.hexdigits) for _ in range(18)])


@AsyncSterilization
class TwitchMessageModal(nextcord.ui.Modal):
    embed = None

    async def __init__(self, guild: nextcord.Guild, selected_id: str, data: dict):
        gdb = GuildDateBases(guild.id)
        locale = await gdb.get('language')

        self.selected_id = selected_id
        self.data = data

        super().__init__(i18n.t(locale, 'settings.notifi.twitch.title'))

        self.message = nextcord.ui.TextInput(
            label=i18n.t(locale, 'settings.notifi.message.title'),
            placeholder=i18n.t(locale, 'settings.notifi.message.placeholder'),
            style=nextcord.TextInputStyle.paragraph,
            default_value=data.get('message')
        )
        self.add_item(self.message)

    async def callback(self, interaction: nextcord.Interaction[LordBot]) -> None:
        await interaction.response.defer()

        message = self.message.value
        self.data['message'] = message

        view = await TwitchItemView(interaction.guild, self.selected_id, self.data)
        await interaction.message.edit(embed=view.embed, view=view)


@AsyncSterilization
class TwitchItemModal(nextcord.ui.Modal):
    async def __init__(self, guild: nextcord.Guild, selected_id: Optional[str] = None, data: Optional[dict] = None):
        gdb = GuildDateBases(guild.id)
        locale = await gdb.get('language')

        self.selected_id = selected_id
        self.data = data

        super().__init__(i18n.t(locale, 'settings.notifi.twitch.title'))

        self.username = nextcord.ui.TextInput(
            label=i18n.t(locale, 'settings.notifi.twitch.modal.label'),
            placeholder=i18n.t(
                locale, 'settings.notifi.twitch.modal.placeholder'),
        )
        self.add_item(self.username)

    async def callback(self, interaction: nextcord.Interaction[LordBot]) -> None:
        await interaction.response.defer()

        gdb = GuildDateBases(interaction.guild_id)
        locale = await gdb.get('language')
        twitch_data = await gdb.get('twitch_notification')
        if self.data is None and self.selected_id is not None:
            self.data = twitch_data.get(self.selected_id)

        username = self.username.value

        if match := re.fullmatch(r'(https://www.twitch.tv/)?([\w]{2,24})', username):
            username = match.group(2)
        else:
            await interaction.followup.send(i18n.t(locale, 'settings.notifi.twitch.modal.error'),
                                            ephemeral=True)
            return

        user = await interaction.client.twnoti.api.get_user_info(username)
        if user is None:
            await interaction.followup.send(i18n.t(locale, 'settings.notifi.twitch.modal.error'),
                                            ephemeral=True)
            return

        if self.data is None:
            self.data = {'id': generate_hex()}

        self.data['username'] = username

        view = await TwitchItemView(interaction.guild, self.data['id'], self.data)
        await interaction.message.edit(embed=view.embed, view=view)


@AsyncSterilization
class TwitchChannelDropDown(nextcord.ui.ChannelSelect):
    async def __init__(self, guild: nextcord.Guild, selected_id: str, data: dict):
        gdb = GuildDateBases(guild.id)
        locale = await gdb.get('language')

        self.selected_id = selected_id
        self.data = data

        super().__init__(placeholder=i18n.t(locale, 'settings.notifi.dropdown.channel'),
                         channel_types=[nextcord.ChannelType.text, nextcord.ChannelType.news])

    async def callback(self, interaction: nextcord.Interaction) -> None:
        channel = self.values[0]
        self.data['channel_id'] = channel.id
        view = await TwitchItemView(interaction.guild, self.selected_id, self.data)
        await interaction.response.edit_message(embed=view.embed, view=view)


@AsyncSterilization
class TwitchItemView(nextcord.ui.View):
    embed: nextcord.Embed

    async def __init__(self, guild: nextcord.Guild, selected_id: str, data: Optional[dict] = None):
        gdb = GuildDateBases(guild.id)
        color = await gdb.get('color')
        locale = await gdb.get('language')
        twitch_data = await gdb.get('twitch_notification')

        if selected_id in twitch_data and not data:
            data = twitch_data[selected_id]

        self.selected_id = selected_id
        self.data = data
        userinfo = None

        if 'username' in data:
            username = data['username']
            bot: LordBot = guild._state._get_client()

            if username in bot.twnoti.user_info:
                userinfo = bot.twnoti.user_info[username]
            else:
                userinfo = await bot.twnoti.api.get_user_info(username)

        user = f'{userinfo.display_name} ({userinfo.login})' if userinfo else i18n.t(
            'settings.notifi.unspecified')
        channel_name = channel.mention if (channel := guild.get_channel(
            data.get('channel_id'))) else i18n.t('settings.notifi.unspecified')

        self.embed = nextcord.Embed(
            title=i18n.t(locale, 'settings.notifi.twitch.title'),
            color=color,
            description=i18n.t(locale, 'settings.notifi.twitch.description')
        )
        self.embed.set_thumbnail(
            userinfo.profile_image_url if userinfo else None)
        self.embed.add_field(
            name='',
            value=i18n.t(locale, 'settings.notifi.twitch.field',
                         user=user, channel=channel_name)
        )

        super().__init__()

        if (('channel_id' in data and 'username' in data)
            and (selected_id not in twitch_data
                 or data != twitch_data[selected_id])):
            self.save.disabled = False

        if selected_id in twitch_data:
            self.delete.disabled = False

        self.add_item(await TwitchChannelDropDown(guild, selected_id, data))

        self.back.label = i18n.t(locale, 'settings.button.back')
        self.save.label = i18n.t(locale, 'settings.button.save_changes')
        self.delete.label = i18n.t(locale, 'settings.button.delete')
        self.view_message.label = i18n.t(
            locale, 'settings.button.preview_message')
        self.change_message.label = i18n.t(
            locale, 'settings.button.change_message')
        self.change_username.label = i18n.t(
            locale, 'settings.button.change_username')

    @nextcord.ui.button(label='Back', style=nextcord.ButtonStyle.red, row=1)
    async def back(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        view = await TwitchView(interaction.guild)
        await interaction.response.edit_message(embed=view.embed, view=view)

    @nextcord.ui.button(label='Save changes', style=nextcord.ButtonStyle.green, row=1, disabled=True)
    async def save(self, button: nextcord.ui.Button, interaction: nextcord.Interaction[LordBot]):
        gdb = GuildDateBases(interaction.guild_id)
        await gdb.set_on_json('twitch_notification', self.selected_id, self.data)

        await interaction.client.twnoti.add_channel(interaction.guild_id, self.data['username'])

        view = await TwitchItemView(interaction.guild, self.selected_id)
        await interaction.response.edit_message(embed=view.embed, view=view)

    @nextcord.ui.button(label='Delete', style=nextcord.ButtonStyle.red, row=1, disabled=True)
    async def delete(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        gdb = GuildDateBases(interaction.guild_id)
        twitch_data = await gdb.get('twitch_notification')
        twitch_data.pop(self.selected_id, None)
        await gdb.set('twitch_notification', twitch_data)

    @nextcord.ui.button(label='Preview message', style=nextcord.ButtonStyle.success, row=2)
    async def view_message(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        message = self.data.get('message', DEFAULT_TWITCH_MESSAGE)
        data = generate_message(message)
        await interaction.response.send_message(**data, ephemeral=True)

    @nextcord.ui.button(label='Change message', style=nextcord.ButtonStyle.blurple, row=2)
    async def change_message(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        modal = await TwitchMessageModal(interaction.guild, self.selected_id, self.data)
        await interaction.response.send_modal(modal)

    @nextcord.ui.button(label='Change username', style=nextcord.ButtonStyle.grey, row=2)
    async def change_username(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        modal = await TwitchItemModal(interaction.guild, self.selected_id, self.data)
        await interaction.response.send_modal(modal)


@AsyncSterilization
class TwitchItemsDropDown(nextcord.ui.StringSelect):
    async def __init__(self, guild: nextcord.Guild):
        gdb = GuildDateBases(guild.id)
        locale = await gdb.get('language')
        twitch_data = await gdb.get('twitch_notification')

        options = [
            nextcord.SelectOption(
                label=data['username'],
                value=id,
                description=str(channel)
            )
            for id, data in twitch_data.items()
            if (channel := guild.get_channel(data['channel_id']))
        ]
        disabled = len(options) == 0
        if disabled:
            options.append(nextcord.SelectOption(label='SelectOption'))

        super().__init__(placeholder=i18n.t(locale, 'settings.notifi.twitch.dropdown'),
                         options=options, disabled=disabled)

    async def callback(self, interaction: nextcord.Interaction) -> None:
        value = self.values[0]

        view = await TwitchItemView(interaction.guild, value)
        await interaction.response.edit_message(embed=view.embed, view=view)


@AsyncSterilization
class TwitchView(DefaultSettingsView):
    embed: nextcord.Embed

    async def __init__(self, guild: nextcord.Guild):
        gdb = GuildDateBases(guild.id)
        color = await gdb.get('color')
        locale = await gdb.get('language')

        self.embed = nextcord.Embed(
            title=i18n.t(locale, 'settings.notifi.twitch.title'),
            color=color,
            description=i18n.t(locale, 'settings.notifi.twitch.description')
        )

        super().__init__()

        self.add_item(await TwitchItemsDropDown(guild))

        self.back.label = i18n.t(locale, 'settings.button.back')
        self.add.label = i18n.t(locale, 'settings.button.add')

    @nextcord.ui.button(label='Back', style=nextcord.ButtonStyle.red)
    async def back(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        view = await notification.NotificationView(interaction.guild)
        await interaction.response.edit_message(embed=view.embed, view=view)

    @nextcord.ui.button(label='Add', style=nextcord.ButtonStyle.green)
    async def add(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        modal = await TwitchItemModal(interaction.guild)
        await interaction.response.send_modal(modal)
