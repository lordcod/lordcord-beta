from __future__ import annotations
from typing import Optional, TYPE_CHECKING, cast

import nextcord

from bot.databases.handlers.guildHD import GuildDateBases
from bot.languages import i18n
from bot.misc.utils import AsyncSterilization


if TYPE_CHECKING:
    from bot.misc.lordbot import LordBot


@AsyncSterilization
class TelegramItemView(nextcord.ui.View):
    embed: nextcord.Embed

    async def __init__(self, guild: nextcord.Guild, selected_id: str, data: Optional[dict] = None):
        from .dropdowns import TelegramChannelDropDown

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
        from .views import TelegramView
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
        from .views import TelegramView

        gdb = GuildDateBases(interaction.guild_id)
        telegram_data = await gdb.get('telegram_notification')
        telegram_data.pop(self.selected_id, None)
        await gdb.set('telegram_notification', telegram_data)

        view = await TelegramView(interaction.guild)
        await interaction.response.edit_message(embed=view.embed, view=view)
