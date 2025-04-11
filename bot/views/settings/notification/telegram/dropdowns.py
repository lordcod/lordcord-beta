from __future__ import annotations
import nextcord
from bot.databases.handlers.guildHD import GuildDateBases
from bot.languages import i18n
from bot.misc.utils import AsyncSterilization


@AsyncSterilization
class TelegramChannelDropDown(nextcord.ui.ChannelSelect):
    async def __init__(self, guild: nextcord.Guild, selected_id: str, data: dict):
        gdb = GuildDateBases(guild.id)
        locale = await gdb.get('language')
        self.selected_id = selected_id
        self.data = data

        super().__init__(
            placeholder=i18n.t(locale, 'settings.notifi.dropdown.channel'),
            channel_types=[nextcord.ChannelType.text,
                           nextcord.ChannelType.news]
        )

    async def callback(self, interaction: nextcord.Interaction) -> None:
        from .items import TelegramItemView
        value = self.values[0]
        view = await TelegramItemView(interaction.guild, value)
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
            options.append(nextcord.SelectOption(label='SelectOption'))

        super().__init__(
            placeholder=i18n.t(locale, 'settings.notifi.telegram.dropdown'),
            options=options,
            disabled=not bool(telegram_data)
        )

    async def callback(self, interaction: nextcord.Interaction) -> None:
        value = self.values[0]
        from .items import TelegramItemView
        view = await TelegramItemView(interaction.guild, value)
        await interaction.response.edit_message(embed=view.embed, view=view)
