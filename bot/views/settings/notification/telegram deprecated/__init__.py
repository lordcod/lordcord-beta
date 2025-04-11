from __future__ import annotations

import random
import string
from typing import TYPE_CHECKING, Optional, cast

import aiogram
import nextcord
from aiogram.utils.deep_linking import create_start_link

from bot.databases.handlers.guildHD import GuildDateBases
from bot.languages import i18n
from bot.misc.utils import AsyncSterilization, Tokenizer
from bot.views.settings import notification
from bot.views.settings._view import DefaultSettingsView

if TYPE_CHECKING:
    from bot.misc.lordbot import LordBot

secret_key = Tokenizer.generate_key()


def generate_hex() -> str:
    return ''.join(random.choices(string.hexdigits, k=18))


@AsyncSterilization
class TelegramChannelDropDown(nextcord.ui.ChannelSelect):
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
        view = await TelegramItemView(interaction.guild, self.selected_id, self.data)
        await interaction.response.edit_message(embed=view.embed, view=view)


@AsyncSterilization
class TelegramItemView(nextcord.ui.View):
    embed: nextcord.Embed

    async def __init__(self, guild: nextcord.Guild, selected_id: str, data: Optional[dict] = None):
        gdb = GuildDateBases(guild.id)
        color = await gdb.get('color')
        locale = await gdb.get('language')
        telegram_data = await gdb.get('telegram_notification')

        if selected_id in telegram_data and not data:
            data = telegram_data[selected_id]

        self.selected_id = selected_id
        self.data = data
        avatar = None

        if 'chat_id' in data:
            chat_id = data['chat_id']
            bot: LordBot = guild._state._get_client()
            avatar = f'{bot.API_URL}/telegram/icon/{chat_id}'

        user = (
            f'{data["title"]} ({data["username"]})'
            if {'username', 'title'} & data.keys()
            else i18n.t(locale, 'settings.notifi.unspecified')
        )

        channel = guild.get_channel(data.get('channel_id'))
        channel_name = channel.mention if channel else i18n.t(
            locale, 'settings.notifi.unspecified')

        self.embed = nextcord.Embed(
            title='Telegram',
            color=color,
            description=i18n.t(
                locale, 'settings.notifi.telegram.description_item')
        )
        if avatar:
            self.embed.set_thumbnail(url=avatar)

        self.embed.add_field(
            name='',
            value=i18n.t(locale, 'settings.notifi.telegram.field',
                         user=user, channel=channel_name)
        )

        super().__init__()

        if not {'chat_id', 'channel_id'} - data.keys() and (
            selected_id not in telegram_data or data != telegram_data[selected_id]
        ):
            self.save.disabled = False

        if selected_id in telegram_data:
            self.delete.disabled = False

        self.add_item(await TelegramChannelDropDown(guild, selected_id, data))

        self.back.label = i18n.t(locale, 'settings.button.back')
        self.save.label = i18n.t(locale, 'settings.button.save_changes')
        self.delete.label = i18n.t(locale, 'settings.button.delete')

    @nextcord.ui.button(label='Back', style=nextcord.ButtonStyle.red, row=1)
    async def back(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        view = await TelegramView(interaction.guild)
        await interaction.response.edit_message(embed=view.embed, view=view)

    @nextcord.ui.button(label='Save changes', style=nextcord.ButtonStyle.green, row=1, disabled=True)
    async def save(self, button: nextcord.ui.Button, interaction: nextcord.Interaction[LordBot]):
        gdb = GuildDateBases(interaction.guild_id)
        await gdb.set_on_json('telegram_notification', self.selected_id, self.data)

        view = await TelegramItemView(interaction.guild, self.selected_id)
        await interaction.response.edit_message(embed=view.embed, view=view)

    @nextcord.ui.button(label='Delete', style=nextcord.ButtonStyle.red, row=1, disabled=True)
    async def delete(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        gdb = GuildDateBases(interaction.guild_id)
        telegram_data = await gdb.get('telegram_notification')
        telegram_data.pop(self.selected_id, None)
        await gdb.set('telegram_notification', telegram_data)


@AsyncSterilization
class TelegramWaitingView(DefaultSettingsView):
    embed: nextcord.Embed

    async def __init__(self, guild: nextcord.Guild, request_id: int):
        super().__init__(timeout=60 * 20)

        bot = guild._state._get_client()
        locale = await GuildDateBases(guild.id).get('language')

        self.guild = guild
        self.embed = nextcord.Embed(
            title=i18n.t(locale, 'settings.notifi.telegram.waiting_title')
        )

        self.add_item(nextcord.ui.Button(
            label=i18n.t(locale, 'settings.notifi.telegram.link_button'),
            url=await create_start_link(bot.telegram_client, request_id, encode=True)
        ))

    @nextcord.ui.button(label="Back", style=nextcord.ButtonStyle.red)
    async def back(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        view = await TelegramView(interaction.guild)
        await interaction.response.edit_message(embed=view.embed, view=view)


@AsyncSterilization
class TelegramItemsDropDown(nextcord.ui.StringSelect):
    async def __init__(self, guild: nextcord.Guild):
        gdb = GuildDateBases(guild.id)
        locale = await gdb.get('language')
        telegram_data = await gdb.get('telegram_notification', {})

        options = [
            nextcord.SelectOption(
                label=f"{data['title']} ({data['username']})",
                value=id,
                description=str(channel)
            )
            for id, data in telegram_data.items()
            if (channel := guild.get_channel(data.get('channel_id')))
        ]

        if not options:
            options.append(nextcord.SelectOption(
                label=i18n.t(locale, 'settings.dropdown.no_items')))

        super().__init__(
            placeholder=i18n.t(locale, 'settings.notifi.telegram.dropdown'),
            options=options,
            disabled=not bool(telegram_data)
        )

    async def callback(self, interaction: nextcord.Interaction) -> None:
        value = self.values[0]
        view = await TelegramItemView(interaction.guild, value)
        await interaction.response.edit_message(embed=view.embed, view=view)


@AsyncSterilization
class TelegramView(DefaultSettingsView):
    embed: nextcord.Embed

    async def __init__(self, guild: nextcord.Guild):
        gdb = GuildDateBases(guild.id)
        color = await gdb.get('color')
        locale = await gdb.get('language')

        self.embed = nextcord.Embed(
            title=i18n.t(locale, 'settings.notifi.telegram.title'),
            color=color,
            description=i18n.t(locale, 'settings.notifi.telegram.description')
        )

        super().__init__()

        self.add_item(await TelegramItemsDropDown(guild))

        self.back.label = i18n.t(locale, 'settings.button.back')
        self.add.label = i18n.t(locale, 'settings.button.add')

    @nextcord.ui.button(label='Back', style=nextcord.ButtonStyle.red)
    async def back(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        modal = await notification.NotificationView(interaction.guild)
        await interaction.response.edit_message(modal)

    @nextcord.ui.button(label='Add', style=nextcord.ButtonStyle.green)
    async def add(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        request_id = random.randint(1_000_000, 1_000_000_000)

        def check_registration(id: str, chat: aiogram.types.ChatShared):
            return int(id) == request_id

        view = await TelegramWaitingView(interaction.guild, request_id)
        await interaction.response.edit_message(embed=view.embed, view=view)

        _, chat = await interaction.client.wait_for('tg_channel_joined', check=check_registration)
        chat = cast(aiogram.types.ChatShared, chat)

        id = generate_hex()
        data = {
            'id': id,
            'chat_id': chat.chat_id,
            'title': chat.title,
            'username': chat.username
        }

        view = await TelegramItemView(interaction.guild, id, data)
        await interaction.message.edit(embed=view.embed, view=view)
