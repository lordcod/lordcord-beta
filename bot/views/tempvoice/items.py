from __future__ import annotations
from enum import IntEnum
from typing import Optional

import nextcord
from bot.databases import localdb
from bot.databases.handlers.guildHD import GuildDateBases
from bot.languages import i18n


class VoiceStatus(IntEnum):
    opened = 1
    closed = 2


async def get_voice(interaction: nextcord.Interaction) -> Optional[nextcord.VoiceChannel]:
    channels_tracks_db = await localdb.get_table('channels_track_data')
    channels_data = await localdb.get_table('channels_data')
    channels_track_data = await channels_tracks_db.get(interaction.guild.id, [])

    for cid in channels_track_data:
        voice_data = await channels_data.get(cid)
        owner_id = voice_data['owner_id']
        status = voice_data['status']
        if interaction.user.id == owner_id and status == VoiceStatus.opened:
            return interaction.guild.get_channel(cid)
    return None


class VoiceUserSelect(nextcord.ui.UserSelect):
    content_key: Optional[str] = None
    content: Optional[str] = None

    def __init__(self, locale: str) -> None:
        placeholder = i18n.t(locale, 'tempvoice.items.select.user')
        if self.content_key is not None:
            self.content = i18n.t(locale, self.content_key)
        super().__init__(placeholder=placeholder)

    def get_view(self):
        view = nextcord.ui.View(timeout=300)
        view.add_item(self)
        return view


class OwnerSettingsDropDown(VoiceUserSelect):
    content_key = 'tempvoice.items.select.owner.placeholder'

    async def callback(self, interaction: nextcord.Interaction) -> None:
        gdb = GuildDateBases(interaction.guild_id)
        locale = await gdb.get('language')

        user = self.values[0]
        if user == interaction.user:
            await interaction.response.edit_message(content=i18n.t(locale, 'tempvoice.errors.himself'), view=None)
            return

        channels_data = await localdb.get_table('channels_data')
        voice = await get_voice(interaction)

        voice_data = await channels_data.get(voice.id)
        voice_data['owner_id'] = user.id
        await channels_data.set(voice.id, voice_data)

        await voice.set_permissions(user, overwrite=nextcord.PermissionOverwrite(
            manage_channels=True,
            manage_permissions=True,
            create_instant_invite=True,
            view_channel=True,
            connect=True,
            speak=True,
            stream=True,
            use_voice_activation=True,
            priority_speaker=True,
            read_message_history=True,
        ))
        await voice.set_permissions(interaction.user, overwrite=None)
        await interaction.response.edit_message(content=i18n.t(locale, 'tempvoice.items.select.owner.success', mention=user.mention),
                                                view=None)


class UserPermissionSettingsDropDown(VoiceUserSelect):
    content_key = 'tempvoice.items.select.perm.placeholder'

    async def callback(self, interaction: nextcord.Interaction) -> None:
        gdb = GuildDateBases(interaction.guild_id)
        locale = await gdb.get('language')

        user = self.values[0]
        if user == interaction.user:
            await interaction.response.edit_message(content=i18n.t(locale, 'tempvoice.errors.himself'), view=None)
            return

        voice = await get_voice(interaction)

        perm = voice.overwrites.get(user)
        if perm is None:
            perm = nextcord.PermissionOverwrite()

        if not (perm.view_channel or perm.connect):
            perm.view_channel = True
            perm.connect = True
            await voice.set_permissions(
                target=user,
                overwrite=perm
            )
            await interaction.response.edit_message(content=i18n.t(locale, 'tempvoice.items.select.permit.success', mention=user.mention),
                                                    view=None)
        else:
            perm.view_channel = False
            perm.connect = False
            await voice.set_permissions(
                target=user,
                overwrite=perm
            )
            await interaction.response.edit_message(content=i18n.t(locale, 'tempvoice.items.select.reject.success', mention=user.mention),
                                                    view=None)


class UserPermitSettingsDropDown(VoiceUserSelect):
    content_key = 'tempvoice.items.select.permit.placeholder'

    async def callback(self, interaction: nextcord.Interaction) -> None:
        gdb = GuildDateBases(interaction.guild_id)
        locale = await gdb.get('language')

        user = self.values[0]
        if user == interaction.user:
            await interaction.response.edit_message(content=i18n.t(locale, 'tempvoice.errors.himself'), view=None)
            return

        voice = await get_voice(interaction)
        perm = voice.overwrites.get(user)
        if perm is None:
            perm = nextcord.PermissionOverwrite()

        perm.view_channel = True
        perm.connect = True
        await voice.set_permissions(
            target=user,
            overwrite=perm
        )

        await interaction.response.edit_message(content=i18n.t(locale, 'tempvoice.items.select.permit.success', mention=user.mention),
                                                view=None)


class UserSettingsRejectDropDown(VoiceUserSelect):
    content_key = 'tempvoice.items.select.reject.placeholder'

    async def callback(self, interaction: nextcord.Interaction) -> None:
        gdb = GuildDateBases(interaction.guild_id)
        locale = await gdb.get('language')

        user = self.values[0]
        if user == interaction.user:
            await interaction.response.edit_message(content=i18n.t(locale, 'tempvoice.errors.himself'), view=None)
            return

        voice = await get_voice(interaction)
        perm = voice.overwrites.get(user)
        if perm is None:
            perm = nextcord.PermissionOverwrite()

        perm.view_channel = False
        perm.connect = False
        await voice.set_permissions(
            target=user,
            overwrite=perm
        )

        await interaction.response.edit_message(content=i18n.t(locale, 'tempvoice.items.select.reject.success', mention=user.mention),
                                                view=None)


class UserKickSettingsDropDown(VoiceUserSelect):
    content_key = 'tempvoice.items.select.kick.placeholder'

    async def callback(self, interaction: nextcord.Interaction) -> None:
        gdb = GuildDateBases(interaction.guild_id)
        locale = await gdb.get('language')

        user = self.values[0]
        if user == interaction.user:
            await interaction.response.edit_message(content=i18n.t(locale, 'tempvoice.errors.himself'), view=None)
            return

        voice = await get_voice(interaction)
        if user not in voice.members:
            await interaction.response.edit_message(content=i18n.t(locale, 'tempvoice.errors.not_user'), view=None)
            return

        await user.disconnect()
        await interaction.response.edit_message(content=i18n.t(locale, 'tempvoice.items.select.kick.success', mention=user.mention),
                                                view=None)


class UserInviteSettingsDropDown(VoiceUserSelect):
    content_key = 'tempvoice.items.select.invite.placeholder'

    async def callback(self, interaction: nextcord.Interaction) -> None:
        gdb = GuildDateBases(interaction.guild_id)
        locale = await gdb.get('language')

        user = self.values[0]
        if user == interaction.user:
            await interaction.response.edit_message(content=i18n.t(locale, 'tempvoice.errors.himself'), view=None)
            return

        voice = await get_voice(interaction)
        if user in voice.members:
            await interaction.response.edit_message(content=i18n.t(locale, 'tempvoice.errors.found_user'), view=None)
            return

        invite = await voice.create_invite(max_uses=1, max_age=30*60)
        await user.send(i18n.t(locale, 'tempvoice.items.select.invite.message', name=interaction.user.name, invite=invite.url))
        await interaction.response.edit_message(content=i18n.t(locale, 'tempvoice.items.select.invite.success', mention=user.mention),
                                                view=None)


class UserMuteSettingsDropDown(VoiceUserSelect):
    content_key = 'tempvoice.items.select.mute_univ.placeholder'

    async def callback(self, interaction: nextcord.Interaction) -> None:
        gdb = GuildDateBases(interaction.guild_id)
        locale = await gdb.get('language')

        user = self.values[0]
        if user == interaction.user:
            await interaction.response.edit_message(content=i18n.t(locale, 'tempvoice.errors.himself'), view=None)
            return

        voice = await get_voice(interaction)
        if user not in voice.members:
            await interaction.response.edit_message(content=i18n.t(locale, 'tempvoice.errors.not_user'), view=None)
            return

        channels_data = await localdb.get_table('channels_data')
        data = await channels_data.get(voice.id)
        mutes = data.get('mutes', {})

        if mutes.get(user.id, True) and user.voice.mute:
            mutes[user.id] = False
            await user.edit(mute=False)
            await interaction.response.edit_message(content=i18n.t(locale, 'tempvoice.items.select.unmute.success', mention=user.mention),
                                                    view=None)
        else:
            mutes[user.id] = True
            await user.edit(mute=True)
            await interaction.response.edit_message(content=i18n.t(locale, 'tempvoice.items.select.mute.success', mention=user.mention),
                                                    view=None)
        data['mutes'] = mutes
        await channels_data.set(voice.id, data)


class UserMuteFDSettingsDropDown(VoiceUserSelect):
    content_key = 'tempvoice.items.select.mute.placeholder'

    async def callback(self, interaction: nextcord.Interaction) -> None:
        gdb = GuildDateBases(interaction.guild_id)
        locale = await gdb.get('language')

        user = self.values[0]
        if user == interaction.user:
            await interaction.response.edit_message(content=i18n.t(locale, 'tempvoice.errors.himself'), view=None)
            return

        voice = await get_voice(interaction)
        if user not in voice.members:
            await interaction.response.edit_message(content=i18n.t(locale, 'tempvoice.errors.not_user'), view=None)
            return

        channels_data = await localdb.get_table('channels_data')
        data = await channels_data.get(voice.id)
        mutes = data.get('mutes', {})
        mutes[user.id] = True

        await user.edit(mute=True)
        await interaction.response.edit_message(content=i18n.t(locale, 'tempvoice.items.select.mute.success', mention=user.mention),
                                                view=None)

        data['mutes'] = mutes
        await channels_data.set(voice.id, data)


class UserUnmuteFDSettingsDropDown(VoiceUserSelect):
    content_key = 'tempvoice.items.select.unmute.placeholder'

    async def callback(self, interaction: nextcord.Interaction) -> None:
        gdb = GuildDateBases(interaction.guild_id)
        locale = await gdb.get('language')

        user = self.values[0]
        if user == interaction.user:
            await interaction.response.edit_message(content=i18n.t(locale, 'tempvoice.errors.himself'), view=None)
            return

        voice = await get_voice(interaction)
        if user not in voice.members:
            await interaction.response.edit_message(content=i18n.t(locale, 'tempvoice.errors.not_user'), view=None)
            return

        channels_data = await localdb.get_table('channels_data')
        data = await channels_data.get(voice.id)
        mutes = data.get('mutes', {})
        mutes[user.id] = False

        await user.edit(mute=False)
        await interaction.response.edit_message(content=i18n.t(locale, 'tempvoice.items.select.unmute.success', mention=user.mention),
                                                view=None)

        data['mutes'] = mutes
        await channels_data.set(voice.id, data)


class LimitSettingsModal(nextcord.ui.Modal):
    def __init__(self, locale: str) -> None:
        super().__init__(i18n.t(locale, 'tempvoice.items.modal.limit.title'))
        self.limit = nextcord.ui.TextInput(
            label=i18n.t(locale, 'tempvoice.items.modal.limit.label'),
            placeholder=i18n.t(locale, 'tempvoice.items.modal.limit.placeholder'),
            max_length=2,
        )
        self.add_item(self.limit)

    async def callback(self, interaction: nextcord.Interaction) -> None:
        gdb = GuildDateBases(interaction.guild_id)
        locale = await gdb.get('language')

        limit = self.limit.value
        if not limit.isdigit() or int(limit) >= 100 or 0 > int(limit):
            await interaction.response.send_message(i18n.t(locale, 'tempvoice.errors.limit_incorrect'),
                                                    ephemeral=True)
            return

        if int(limit) == 0:
            limit = None
        else:
            limit = int(limit)

        voice = await get_voice(interaction)
        await voice.edit(user_limit=limit)
        await interaction.response.send_message(i18n.t(locale, 'tempvoice.items.modal.limit.success'),
                                                ephemeral=True)


class BitrateSettingsModal(nextcord.ui.Modal):
    def __init__(self, locale: str, bitrate_limit: int) -> None:
        super().__init__(i18n.t(locale, 'tempvoice.items.modal.bitrate.title'))
        self.bitrate = nextcord.ui.TextInput(
            label=i18n.t(locale, 'tempvoice.items.modal.bitrate.label'),
            placeholder=i18n.t(locale, 'tempvoice.items.modal.bitrate.placeholder',
                               bitrate_limit=bitrate_limit),
            max_length=3,
        )
        self.add_item(self.bitrate)

    async def callback(self, interaction: nextcord.Interaction) -> None:
        gdb = GuildDateBases(interaction.guild_id)
        locale = await gdb.get('language')

        bitrate = self.bitrate.value
        if not bitrate.isdigit() or int(bitrate) > interaction.guild.bitrate_limit//1000 or 8 > int(bitrate):
            await interaction.response.send_message(i18n.t(locale, 'tempvoice.errors.bitrate_incorrect',
                                                           bitrate_limit=interaction.guild.bitrate_limit//1000),
                                                    ephemeral=True)
            return

        voice = await get_voice(interaction)
        await voice.edit(bitrate=int(bitrate)*1000)
        await interaction.response.send_message(i18n.t(locale, 'tempvoice.items.modal.bitrate.success'),
                                                ephemeral=True)


class NameSettingsModal(nextcord.ui.Modal):
    def __init__(self, locale: str) -> None:
        super().__init__(i18n.t(locale, 'tempvoice.items.modal.name.title'))
        self.name = nextcord.ui.TextInput(
            label=i18n.t(locale, 'tempvoice.items.modal.name.label'),
            placeholder=i18n.t(locale, 'tempvoice.items.modal.name.placeholder'),
            max_length=100,
        )
        self.add_item(self.name)

    async def callback(self, interaction: nextcord.Interaction) -> None:
        gdb = GuildDateBases(interaction.guild_id)
        locale = await gdb.get('language')
        name = self.name.value

        voice = await get_voice(interaction)
        await voice.edit(name=name)

        await interaction.response.send_message(i18n.t(locale, 'tempvoice.items.modal.name.success'),
                                                ephemeral=True)
