from typing import List, Optional


from bot.databases.varstructs import LogsPayload
from bot.languages import i18n
from bot.databases import GuildDateBases
import nextcord
from bot.misc.plugins import logstool
from bot.misc.lordbot import LordBot
from bot.misc.utils import AsyncSterilization

from bot.resources.ether import Emoji
from bot.views import settings_menu
from ._view import DefaultSettingsView
from bot.misc.plugins.logstool import LogType


logs_items: List[LogType] = [
    log
    for log in LogType.__dict__.values()
    if isinstance(log, LogType)
]


@AsyncSterilization
class ChannelSetDropDown(nextcord.ui.StringSelect):
    async def __init__(self, guild: nextcord.Guild, selected_channel_id: Optional[int] = None):
        gdb = GuildDateBases(guild.id)
        locale = await gdb.get('language')
        logs_data = await gdb.get('logs')
        options = [
            nextcord.SelectOption(
                label=channel.name,
                value=channel_id,
                description=', '.join(
                    [i18n.t(locale, f'settings.logs.items.{log_item.name}.title') for log_item in logs_items if log_item.value in log_ids]).capitalize()[:100],
                emoji=Emoji.channel_text,
                default=channel_id == selected_channel_id
            )
            for channel_id, log_ids in logs_data.items()
            if (channel := guild.get_channel(channel_id))
        ]
        disabled = len(options) == 0
        if disabled:
            options.append(nextcord.SelectOption(label='SelectOption'))

        super().__init__(placeholder=i18n.t(locale, "settings.logs.set-channel"),
                         options=options,
                         disabled=disabled)

    async def callback(self, interaction: nextcord.Interaction) -> None:
        view = await LogsView(interaction.guild, int(self.values[0]))
        await interaction.message.edit(embed=view.embed, view=view)


@AsyncSterilization
class ChannelDropDown(nextcord.ui.ChannelSelect):
    async def __init__(self, guild_id: int):
        gdb = GuildDateBases(guild_id)
        locale = await gdb.get('language')
        super().__init__(
            placeholder=i18n.t(locale, "settings.logs.channel"),
            channel_types=[nextcord.ChannelType.news,
                           nextcord.ChannelType.text]
        )

    async def callback(self, interaction: nextcord.Interaction) -> None:
        view = await LogsView(interaction.guild,  self.values[0].id)
        await interaction.message.edit(embed=view.embed, view=view)


@AsyncSterilization
class LogsDropDown(nextcord.ui.StringSelect):
    async def __init__(self, guild_id: int, selected_channel_id: Optional[int] = None,
                       selected_logs: Optional[List[int]] = None):
        gdb = GuildDateBases(guild_id)
        locale = await gdb.get('language')
        logs_data: LogsPayload = await gdb.get('logs')
        channel_data = logs_data.get(selected_channel_id, [])
        self.selected_channel_id = selected_channel_id

        if selected_logs:
            channel_data = selected_logs

        options = [
            nextcord.SelectOption(
                label=i18n.t(locale, f'settings.logs.items.{log.name}.title'),
                description=i18n.t(
                    locale, f'settings.logs.items.{log.name}.description')[:100],
                value=log.value,
                default=log.value in channel_data
            )
            for log in logs_items
        ]

        super().__init__(
            placeholder=i18n.t(locale, "settings.logs.type"),
            min_values=1,
            max_values=len(options),
            options=options,
            disabled=not selected_channel_id
        )

    async def callback(self, interaction: nextcord.Interaction) -> None:
        values = list(map(int, self.values))

        view = await LogsView(interaction.guild,  self.selected_channel_id, values)
        await interaction.message.edit(embed=view.embed, view=view)


@AsyncSterilization
class LogsView(DefaultSettingsView):
    embed: nextcord.Embed

    async def __init__(
        self,
        guild: nextcord.Guild,
        selected_channel_id: Optional[int] = None,
        selected_logs: Optional[List[int]] = None
    ) -> None:
        self.selected_channel_id = selected_channel_id
        self.selected_logs = selected_logs
        gdb = GuildDateBases(guild.id)
        logs_data: LogsPayload = await gdb.get('logs')
        color = await gdb.get('color')
        locale = await gdb.get('language')

        self.embed = nextcord.Embed(
            title=i18n.t(locale, 'settings.logs.embed.title'),
            description=i18n.t(locale, 'settings.logs.embed.description'),
            color=color
        )

        super().__init__()

        if selected_logs:
            self.save.disabled = False
        if selected_channel_id in logs_data:
            self.delete.disabled = False

        self.back.label = i18n.t(locale, 'settings.button.back')
        self.save.label = i18n.t(locale, 'settings.button.save_changes')
        self.delete.label = i18n.t(locale, 'settings.button.delete')

        self.add_item(await ChannelSetDropDown(guild, selected_channel_id))
        self.add_item(await ChannelDropDown(guild.id))
        self.add_item(await LogsDropDown(
            guild.id, selected_channel_id, selected_logs))

    @nextcord.ui.button(label='Back', style=nextcord.ButtonStyle.red)
    async def back(self,
                   button: nextcord.ui.Button,
                   interaction: nextcord.Interaction):
        view = await settings_menu.SettingsView(interaction.user)

        await interaction.message.edit(embed=view.embed, view=view)

    @nextcord.ui.button(label='Save changes', style=nextcord.ButtonStyle.blurple, disabled=True)
    async def save(self,
                   button: nextcord.ui.Button,
                   interaction: nextcord.Interaction[LordBot]):
        channel = interaction.guild.get_channel(self.selected_channel_id)
        await logstool.get_webhook(channel)

        gdb = GuildDateBases(interaction.guild_id)
        await gdb.set_on_json(
            'logs',
            self.selected_channel_id,
            self.selected_logs
        )

        view = await LogsView(interaction.guild, self.selected_channel_id)
        await interaction.message.edit(embed=view.embed, view=view)

    @nextcord.ui.button(label='Delete', style=nextcord.ButtonStyle.red, disabled=True)
    async def delete(self,
                     button: nextcord.ui.Button,
                     interaction: nextcord.Interaction):
        gdb = GuildDateBases(interaction.guild_id)
        logs_data: LogsPayload = await gdb.get('logs')
        logs_data.pop(self.selected_channel_id, None)
        await gdb.set('logs', logs_data)

        view = await LogsView(interaction.guild, self.selected_channel_id)

        await interaction.message.edit(embed=view.embed, view=view)
