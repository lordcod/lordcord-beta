from __future__ import annotations

import asyncio
import random
import string
from typing import TYPE_CHECKING, Optional

import nextcord

from bot.databases.handlers.guildHD import GuildDateBases
from bot.languages import i18n
from bot.misc.api.vk_api import VkApi
from bot.misc.utils import AsyncSterilization, Tokenizer
from bot.views.settings import notification
from bot.views.settings._view import DefaultSettingsView

if TYPE_CHECKING:
    from bot.misc.lordbot import LordBot

secret_key = Tokenizer.generate_key()


def generate_hex() -> str:
    return ''.join(random.choices(string.hexdigits, k=18))


@AsyncSterilization
class VkChannelDropDown(nextcord.ui.ChannelSelect):
    async def __init__(self, guild: nextcord.Guild, selected_id: str, data: dict):
        gdb = GuildDateBases(guild.id)
        locale = await gdb.get('language')

        self.selected_id = selected_id
        self.data = data

        placeholder_text = i18n.t(locale, 'settings.notifi.dropdown.channel')
        super().__init__(
            placeholder=placeholder_text,
            channel_types=[nextcord.ChannelType.text,
                           nextcord.ChannelType.news]
        )

    async def callback(self, interaction: nextcord.Interaction) -> None:
        channel = self.values[0]
        self.data['channel_id'] = channel.id
        view = await VkItemView(interaction.guild, self.selected_id, self.data)
        await interaction.response.edit_message(embed=view.embed, view=view)


@AsyncSterilization
class VkItemView(nextcord.ui.View):
    embed: nextcord.Embed

    async def __init__(self, guild: nextcord.Guild, selected_id: str, data: Optional[dict] = None):
        gdb = GuildDateBases(guild.id)
        color = await gdb.get('color')
        locale = await gdb.get('language')
        vk_data = await gdb.get('vk_notification')

        if selected_id in vk_data and not data:
            data = vk_data[selected_id]

        self.selected_id = selected_id
        self.data = data
        avatar = None

        if 'group_id' in data:
            avatar = data.get('photo', None)

        user = (
            f'{data["name"]} ({data["screen_name"]})'
            if {'screen_name', 'name'} & data.keys()
            else i18n.t(locale, 'settings.notifi.unspecified')
        )

        channel = guild.get_channel(data.get('channel_id'))
        channel_name = channel.mention if channel else i18n.t(
            locale, 'settings.notifi.unspecified')

        self.embed = nextcord.Embed(
            title='VK',
            color=color,
            description=i18n.t(
                locale, 'settings.notifi.vk.description_item')
        )
        if avatar:
            self.embed.set_thumbnail(url=avatar)

        self.embed.add_field(
            name='',
            value=i18n.t(locale, 'settings.notifi.vk.field',
                         user=user, channel=channel_name)
        )

        super().__init__()

        if not {'group_id', 'channel_id'} - data.keys() and (
            selected_id not in vk_data or data != vk_data[selected_id]
        ):
            self.save.disabled = False

        if selected_id in vk_data:
            self.delete.disabled = False

        self.add_item(await VkChannelDropDown(guild, selected_id, data))

        self.back.label = i18n.t(locale, 'settings.button.back')
        self.save.label = i18n.t(locale, 'settings.button.save_changes')
        self.delete.label = i18n.t(locale, 'settings.button.delete')

    @nextcord.ui.button(label='Back', style=nextcord.ButtonStyle.red, row=1)
    async def back(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        view = await VkView(interaction.guild)
        await interaction.response.edit_message(embed=view.embed, view=view)

    @nextcord.ui.button(label='Save changes', style=nextcord.ButtonStyle.green, row=1, disabled=True)
    async def save(self, button: nextcord.ui.Button, interaction: nextcord.Interaction[LordBot]):
        gdb = GuildDateBases(interaction.guild_id)
        await gdb.set_on_json('vk_notification', self.selected_id, self.data)

        view = await VkItemView(interaction.guild, self.selected_id)
        await interaction.response.edit_message(embed=view.embed, view=view)

    @nextcord.ui.button(label='Delete', style=nextcord.ButtonStyle.red, row=1, disabled=True)
    async def delete(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        gdb = GuildDateBases(interaction.guild_id)
        vk_data = await gdb.get('vk_notification')
        vk_data.pop(self.selected_id, None)
        await gdb.set('vk_notification', vk_data)

        view = await VkView(interaction.guild)
        await interaction.response.edit_message(embed=view.embed, view=view)


@AsyncSterilization
class VkWaitingView(DefaultSettingsView):
    embed: nextcord.Embed

    async def __init__(self, guild: nextcord.Guild, request_id: int):
        super().__init__(timeout=60 * 20)

        bot: LordBot = guild._state._get_client()
        locale = await GuildDateBases(guild.id).get('language')

        self.guild = guild
        self.embed = nextcord.Embed(
            title=i18n.t(locale, 'settings.notifi.vk.waiting_title')
        )

        self.add_item(nextcord.ui.Button(
            label=i18n.t(locale, 'settings.notifi.vk.link_button'),
            url=f'{bot.SITE_URL}/server-select?state={request_id}'
        ))

    @nextcord.ui.button(label="Back", style=nextcord.ButtonStyle.red)
    async def back(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        view = await VkView(interaction.guild)
        await interaction.response.edit_message(embed=view.embed, view=view)


@AsyncSterilization
class VkItemsDropDown(nextcord.ui.StringSelect):
    async def __init__(self, guild: nextcord.Guild):
        gdb = GuildDateBases(guild.id)
        locale = await gdb.get('language')
        vk_data = await gdb.get('vk_notification', {})

        options = [
            nextcord.SelectOption(
                label=f"{data['name']} ({data['screen_name']})",
                value=id,
                description=str(channel)
            )
            for id, data in vk_data.items()
            if (channel := guild.get_channel(data.get('channel_id')))
        ]

        if not options:
            options.append(nextcord.SelectOption(label='SelectOption'))

        super().__init__(
            placeholder=i18n.t(locale, 'settings.notifi.vk.dropdown'),
            options=options,
            disabled=not bool(vk_data)
        )

    async def callback(self, interaction: nextcord.Interaction) -> None:
        value = self.values[0]
        view = await VkItemView(interaction.guild, value)
        await interaction.response.edit_message(embed=view.embed, view=view)


@AsyncSterilization
class VkView(DefaultSettingsView):
    embed: nextcord.Embed

    async def __init__(self, guild: nextcord.Guild):
        gdb = GuildDateBases(guild.id)
        color = await gdb.get('color')
        locale = await gdb.get('language')

        self.embed = nextcord.Embed(
            title=i18n.t(locale, 'settings.notifi.vk.title'),
            color=color,
            description=i18n.t(locale, 'settings.notifi.vk.description')
        )

        super().__init__()

        self.add_item(await VkItemsDropDown(guild))

        self.back.label = i18n.t(locale, 'settings.button.back')
        self.add.label = i18n.t(locale, 'settings.button.add')

    @nextcord.ui.button(label='Back', style=nextcord.ButtonStyle.red)
    async def back(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        view = await notification.NotificationView(interaction.guild)
        await interaction.response.edit_message(embed=view.embed, view=view)

    @nextcord.ui.button(label='Add', style=nextcord.ButtonStyle.green)
    async def add(self, button: nextcord.ui.Button, interaction: nextcord.Interaction[LordBot]):
        request_id = random.randint(1_000_000, 1_000_000_000)

        view = await VkWaitingView(interaction.guild, request_id)
        await interaction.response.edit_message(embed=view.embed, view=view)

        def check(gid, t, state):
            return int(state) == request_id

        group_id, token, state = await interaction.client.wait_for('vk_club', check=check)

        vk = VkApi(interaction.client, token)
        response = await vk.method('groups.getById',
                                   group_id=group_id)
        group_data = response[0]

        id = generate_hex()
        data = {
            'id': id,
            'group_id': group_data['id'],
            'name': group_data['name'],
            'screen_name': group_data['screen_name'],
            'photo': group_data['photo_200']
        }

        view = await VkItemView(interaction.guild, id, data)
        await interaction.message.edit(embed=view.embed, view=view)
