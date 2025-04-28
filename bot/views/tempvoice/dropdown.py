from __future__ import annotations
from enum import IntEnum
from typing import Optional
import nextcord

from bot.databases.datastore import DataStore
from bot.databases.handlers.guildHD import GuildDateBases
from bot.languages import i18n
from bot.misc.plugins import tempvoice
from bot.misc.utils import AsyncSterilization, get_emoji_wrap
from .information import advance_dd_voice_items, simple_dd_voice_items
from .functions import TempVoiceFunctioins


class VoiceStatus(IntEnum):
    opened = 1
    closed = 2


async def get_voice(interaction: nextcord.Interaction) -> Optional[nextcord.VoiceChannel]:
    channels_tracks_db = DataStore('channels_track_data')
    channels_data = DataStore('channels_data')
    channels_track_data = await channels_tracks_db.get(interaction.guild.id, [])

    for cid in channels_track_data:
        voice_data = await channels_data.get(cid)
        owner_id = voice_data['owner_id']
        status = voice_data['status']
        if interaction.user.id == owner_id and status == VoiceStatus.opened:
            return interaction.guild.get_channel(cid)

# 'Activity' 'NSFW'


@AsyncSterilization
class TempVoiceSettingDropDown(nextcord.ui.StringSelect):
    async def __init__(self, guild_id: Optional[int] = None) -> None:
        if guild_id is None:
            super().__init__(custom_id='tempvoice:dropdown:items:set')
            return

        gdb = GuildDateBases(guild_id)
        data = await gdb.get('tempvoice')
        locale = await gdb.get('language')
        get_emoji = await get_emoji_wrap(gdb)
        if data.get('advance_panel', True):
            iterator = advance_dd_voice_items
        else:
            iterator = simple_dd_voice_items

        super().__init__(custom_id='tempvoice:dropdown:items:set',
                         placeholder=i18n.t(locale, 'tempvoice.dropdown.set'),
                         options=[
                             nextcord.SelectOption(
                                 label=i18n.t(
                                     locale, f"tempvoice.items.description.{opt['value']}.label"),
                                 value=opt['value'],
                                 description=i18n.t(
                                     locale, f"tempvoice.items.description.{opt['value']}.description"),
                                 emoji=get_emoji(opt['emoji']),
                             )
                             for opt in iterator[0]
                         ])

    async def callback(self, interaction: nextcord.Interaction) -> None:
        value = self.values[0]
        await TempVoiceFunctioins().run_interaction(interaction, value)

        await tempvoice.TempVoiceModule.edit_panel_message(interaction.message)


@AsyncSterilization
class TempVoicePersmissionsDropDown(nextcord.ui.StringSelect):
    async def __init__(self, guild_id: Optional[int] = None) -> None:
        if guild_id is None:
            super().__init__(custom_id='tempvoice:dropdown:items:perm')
            return

        gdb = GuildDateBases(guild_id)
        data = await gdb.get('tempvoice')
        locale = await gdb.get('language')
        get_emoji = await get_emoji_wrap(gdb)
        if data.get('advance_panel', True):
            iterator = advance_dd_voice_items
        else:
            iterator = simple_dd_voice_items

        super().__init__(custom_id='tempvoice:dropdown:items:perm',
                         placeholder=i18n.t(locale, 'tempvoice.dropdown.perm'),
                         options=[
                             nextcord.SelectOption(
                                 label=i18n.t(
                                     locale, f"tempvoice.items.description.{opt['value']}.label"),
                                 value=opt['value'],
                                 description=i18n.t(
                                     locale, f"tempvoice.items.description.{opt['value']}.description"),
                                 emoji=get_emoji(opt['emoji']),
                             )
                             for opt in iterator[1]
                         ])

    async def callback(self, interaction: nextcord.Interaction) -> None:
        value = self.values[0]
        await TempVoiceFunctioins().run_interaction(interaction, value)
        await interaction.message.edit(view=self.view)


@AsyncSterilization
class AdvancedTempVoiceView(nextcord.ui.View):
    embed: nextcord.Embed

    async def __init__(self, guild_id: Optional[int] = None) -> None:
        super().__init__(timeout=None)
        if guild_id is None:
            self.add_item(await TempVoiceSettingDropDown())
            self.add_item(await TempVoicePersmissionsDropDown())
            return
        self.add_item(await TempVoiceSettingDropDown(guild_id))
        self.add_item(await TempVoicePersmissionsDropDown(guild_id))

    async def interaction_check(self, interaction: nextcord.Interaction) -> bool:
        gdb = GuildDateBases(interaction.guild_id)
        locale = await gdb.get('language')
        voice = await get_voice(interaction)
        if voice is None:
            await interaction.response.send_message(i18n.t(locale, 'tempvoice.errors.room_not_found'),
                                                    ephemeral=True)
            return False
        return True
