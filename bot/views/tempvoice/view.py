from __future__ import annotations
from enum import IntEnum
from typing import Optional
import nextcord

from bot.databases import GuildDateBases
from bot.databases.datastore import DataStore
from bot.languages import i18n
from bot.misc.utils import AsyncSterilization, get_emoji_wrap
from .information import simple_but_voice_items, advance_but_voice_items
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
    return None


# 'Activity'

@AsyncSterilization
class TempVoiceView(nextcord.ui.View):
    async def __init__(self, guild_id: Optional[int] = None) -> None:
        super().__init__(timeout=None)
        if guild_id is None:
            values = []
            for data in advance_but_voice_items:
                values.append(data['value'])
                but = nextcord.ui.Button(custom_id='tempvoice:'+data['value'])
                but.callback = TempVoiceFunctioins().run_interaction_button
                self.add_item(but)
            for data in simple_but_voice_items:
                if data['value'] in values:
                    continue
                but = nextcord.ui.Button(custom_id='tempvoice:'+data['value'])
                but.callback = TempVoiceFunctioins().run_interaction_button
                self.add_item(but)
            return

        gdb = GuildDateBases(guild_id)
        data = await gdb.get('tempvoice')
        get_emoji = await get_emoji_wrap(gdb)

        if data.get('advance_panel', False):
            iterator = advance_but_voice_items
        else:
            iterator = simple_but_voice_items

        for data in iterator:
            but = nextcord.ui.Button(
                custom_id='tempvoice:'+data['value'],
                emoji=get_emoji(data['emoji']),
                row=data['row']
            )
            but.callback = TempVoiceFunctioins().run_interaction_button
            self.add_item(but)

    async def interaction_check(self, interaction: nextcord.Interaction) -> bool:
        gdb = GuildDateBases(interaction.guild_id)
        locale = await gdb.get('language')
        voice = await get_voice(interaction)
        if voice is None:
            await interaction.response.send_message(i18n.t(locale, 'tempvoice.errors.room_not_found'),
                                                    ephemeral=True)
            return False
        return True
