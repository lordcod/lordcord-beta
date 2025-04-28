import contextlib
from datetime import datetime
from enum import IntEnum
import logging
import time
from typing import Optional
import nextcord
from nextcord.utils import snowflake_time

from bot.databases.datastore import DataStore
from bot.databases.handlers.guildHD import GuildDateBases
from bot.languages import i18n
from bot.misc.utils import get_payload, get_emoji_wrap, lord_format
from bot.views.tempvoice.view import TempVoiceView
from bot.views.tempvoice import dropdown as dropdown_item


_log = logging.getLogger(__name__)

TIMEOUT_VOICE = 5


class VoiceStatus(IntEnum):
    opened = 1
    closed = 2


class TempVoiceModule:
    # TODO: added tempvoice log
    def __init__(self, member: nextcord.Member) -> None:
        self.member = member

    async def process(
        self,
        before: Optional[nextcord.VoiceChannel],
        after: Optional[nextcord.VoiceChannel]
    ) -> None:
        member = self.member

        gdb = GuildDateBases(member.guild.id)
        data = await gdb.get('tempvoice')
        channels_data = DataStore('channels_data')

        if not (data and data.get('enabled')):
            return

        if before:
            voice_data = await channels_data.get(before.id)
            if voice_data and voice_data.get('mutes', {}).get(member.id):
                if after is None:
                    mutes = data.get('mutes', [])
                    mutes.append(member.id)
                    await gdb.set_on_json('tempvoice', 'mutes', mutes)
                else:
                    await member.edit(mute=False)
        if after:
            mutes = data.get('mutes', [])
            voice_data = await channels_data.get(after.id)
            if voice_data and voice_data.get('mutes', {}).get(member.id):
                await member.edit(mute=True)
            elif member.id in mutes:
                mutes.remove(member.id)
                await member.edit(mute=False)
                await gdb.set_on_json('tempvoice', 'mutes', mutes)

        if after and after.id == data['channel_id']:
            await self.create(after)
        if before and await channels_data.exists(before.id):
            await self.delete(before)

    @classmethod
    async def create_panel(cls, guild: nextcord.Guild):
        gdb = GuildDateBases(guild.id)
        data = await gdb.get('tempvoice')
        panel_channel = guild.get_channel(data.get('panel_channel_id'))
        type_panel = data.get('type_panel', 1)

        if data.get('type_message_panel', 1) in {1, 3} and panel_channel:
            if type_panel == 1:
                view = await TempVoiceView(guild.id)
            elif type_panel == 2:
                view = await dropdown_item.AdvancedTempVoiceView(guild.id)
            else:
                view = None

            if view is not None:
                embed = await cls.get_embed(guild)
                message = await panel_channel.send(embed=embed, view=view)
                await gdb.set_on_json('tempvoice', 'panel_message_id',  message.id)

    @classmethod
    async def edit_panel(cls, guild: nextcord.Guild):
        gdb = GuildDateBases(guild.id)
        data = await gdb.get('tempvoice')
        panel_channel = guild.get_channel(data.get('panel_channel_id'))
        panel_message_id = data.get('panel_message_id')

        if panel_message_id is None:
            cls.create_panel(guild)
            return

        if data.get('type_message_panel', 1) in {1, 3} and panel_channel:
            panel_message = panel_channel.get_partial_message(panel_message_id)
            await cls.edit_panel_message(panel_message)

    @staticmethod
    async def get_embed(guild: nextcord.Guild) -> nextcord.Embed:
        gdb = GuildDateBases(guild.id)
        locale = await gdb.get('language')
        color = await gdb.get('color')
        get_emoji = await get_emoji_wrap(gdb)
        emoji = get_emoji('assets')

        embed = nextcord.Embed(
            title=i18n.t(locale, 'tempvoice.panel.message.title', emoji=emoji),
            description=i18n.t(
                locale, 'tempvoice.panel.message.description', emoji=emoji),
            color=color,
            timestamp=datetime.today()
        )
        return embed

    @classmethod
    async def edit_panel_message(cls, message: nextcord.Message):
        guild = message.guild

        gdb = GuildDateBases(guild.id)
        data = await gdb.get('tempvoice')
        type_panel = data.get('type_panel', 1)

        if type_panel == 1:
            view = await TempVoiceView(guild.id)
        elif type_panel == 2:
            view = await dropdown_item.AdvancedTempVoiceView(guild.id)
        else:
            view = None

        if view is not None:
            embed = await cls.get_embed(guild)
            await message.edit(embed=embed, view=view)

    async def check_user(self, channel: nextcord.VoiceChannel):
        gdb = GuildDateBases(self.member.guild.id)
        locale = await gdb.get('language')
        channels_tracks_db = DataStore('channels_track_data')
        channels_data = DataStore('channels_data')
        channels_track_data = await channels_tracks_db.get(self.member.guild.id, [])

        for cid in channels_track_data:
            voice_data = await channels_data.get(cid)
            owner_id = voice_data['owner_id']

            if self.member.id != owner_id:
                continue

            if voice_data['status'] == VoiceStatus.closed:
                limited_time = snowflake_time(cid).timestamp()+TIMEOUT_VOICE
                if limited_time > time.time():
                    with contextlib.suppress(nextcord.Forbidden):
                        await channel.send(i18n.t(locale, 'tempvoice.errors.room_limit',
                                                  mention=self.member.mention, limited_time=limited_time))
                    await self.member.disconnect()
                    return False
            if voice_data['status'] == VoiceStatus.opened:
                channel = self.member.guild.get_channel(
                    voice_data['channel_id'])
                if channel is None:
                    voice_data['status'] = VoiceStatus.closed
                    voice_data['closed_time'] = time.time()
                    await channels_data.set(cid, voice_data)
                    continue
                await self.member.move_to(channel)
                return False
        return True

    async def get_count(self):
        channels_tracks_db = DataStore('channels_track_data')
        channels_data = DataStore('channels_data')
        channels_track_data = await channels_tracks_db.get(self.member.guild.id, [])

        total = 1
        active = 1
        for cid in channels_track_data:
            total += 1
            voice_data = await channels_data.get(cid)
            if voice_data['status'] == VoiceStatus.opened:
                active += 1
        return {
            'active': active,
            'total': total
        }

    async def create(self, channel: nextcord.VoiceChannel):
        if not await self.check_user(channel):
            return

        gdb = GuildDateBases(self.member.guild.id)
        data = await gdb.get('tempvoice')
        channels_tracks_db = DataStore('channels_track_data')
        channels_data = DataStore('channels_data')
        channels_track_data = await channels_tracks_db.get(self.member.guild.id, [])

        type_panel = data.get('type_panel', 1)
        name = lord_format(data.get('channel_name', '{voice.count.active}-{member.username}'),
                           get_payload(member=self.member,
                                       voice_count=await self.get_count()))
        category = self.member.guild.get_channel(data['category_id'])
        channel = await self.member.guild.create_voice_channel(
            name=name,
            category=category,
            user_limit=data.get('channel_limit', 4),
            overwrites={
                self.member: nextcord.PermissionOverwrite(
                    manage_channels=True,
                    manage_permissions=True,
                    create_instant_invite=True,
                    view_channel=True,
                    read_message_history=True,
                    connect=True,
                    speak=True,
                    stream=True,
                    use_voice_activation=True,
                    priority_speaker=True,
                ),
                self.member.guild.default_role: nextcord.PermissionOverwrite(
                    view_channel=True,
                    read_message_history=True,
                    connect=True,
                    speak=True,
                    stream=True,
                    use_voice_activation=True,
                    priority_speaker=True
                )
            })
        await self.member.move_to(channel)

        if data.get('type_message_panel', 1) in {2, 3}:
            if type_panel == 1:
                view = await TempVoiceView(self.member.guild.id)
            elif type_panel == 2:
                view = await dropdown_item.AdvancedTempVoiceView(self.member.guild.id)
            else:
                view = None
            if view is not None:
                embed = await self.get_embed(self.member.guild)
                await channel.send(embed=embed, view=view)

        channels_track_data.append(channel.id)
        await channels_tracks_db.set(self.member.guild.id, channels_track_data)
        await channels_data.set(channel.id, {
            'owner_id': self.member.id,
            'channel_id': channel.id,
            'status': VoiceStatus.opened
        })

    async def delete(self, channel: nextcord.VoiceChannel):
        if len(channel.members) > 0:
            return

        channels_data = DataStore('channels_data')
        voice_data = await channels_data.get(channel.id)
        voice_data['status'] = VoiceStatus.closed
        voice_data['closed_time'] = time.time()
        await channels_data.set(channel.id, voice_data)

        await channel.delete()
