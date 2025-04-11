from __future__ import annotations
from typing import TYPE_CHECKING

import nextcord
from aiogram.utils.deep_linking import create_start_link

from bot.databases.handlers.guildHD import GuildDateBases
from bot.languages import i18n
from bot.misc.utils import AsyncSterilization
from bot.views.settings._view import DefaultSettingsView


if TYPE_CHECKING:
    from bot.misc.lordbot import LordBot


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
        from .views import TelegramView
        view = await TelegramView(interaction.guild)
        await interaction.response.edit_message(embed=view.embed, view=view)
