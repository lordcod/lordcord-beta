from __future__ import annotations
from enum import IntEnum
from typing import Optional
import nextcord

from bot.databases import GuildDateBases
from bot.databases.datastore import DataStore
from bot.languages import i18n
from .items import (
    LimitSettingsModal,
    UserMuteSettingsDropDown,
    UserKickSettingsDropDown,
    UserPermissionSettingsDropDown,
    OwnerSettingsDropDown,
    NameSettingsModal,
    BitrateSettingsModal,
    UserInviteSettingsDropDown,
    UserMuteFDSettingsDropDown,
    UserUnmuteFDSettingsDropDown,
    UserPermitSettingsDropDown,
    UserSettingsRejectDropDown
)


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


class TempVoiceFunctioins:
    def get_module(self, module_name: str):
        return getattr(self, 'process_'+module_name, None)

    async def run_interaction_button(self, interaction: nextcord.Interaction) -> None:
        custom_id = interaction.data['custom_id']
        await self.run_interaction(interaction, custom_id.removeprefix('tempvoice:'))

    async def run_interaction(self, interaction: nextcord.Interaction, value: str) -> None:
        module = self.get_module(value)
        await module(interaction)

    async def process_change_owner(self, interaction: nextcord.Interaction) -> None:
        gdb = GuildDateBases(interaction.guild_id)
        locale = await gdb.get('language')
        dropdown = OwnerSettingsDropDown(locale)
        view = dropdown.get_view()
        await interaction.response.send_message(content=dropdown.content, view=view, ephemeral=True)

    async def process_give_access(self, interaction: nextcord.Interaction) -> None:
        gdb = GuildDateBases(interaction.guild_id)
        locale = await gdb.get('language')
        dropdown = UserPermissionSettingsDropDown(locale)
        view = dropdown.get_view()
        await interaction.response.send_message(content=dropdown.content, view=view, ephemeral=True)

    async def process_kick_member(self, interaction: nextcord.Interaction) -> None:
        gdb = GuildDateBases(interaction.guild_id)
        locale = await gdb.get('language')
        dropdown = UserKickSettingsDropDown(locale)
        view = dropdown.get_view()
        await interaction.response.send_message(content=dropdown.content, view=view, ephemeral=True)

    async def process_mute_member(self, interaction: nextcord.Interaction) -> None:
        gdb = GuildDateBases(interaction.guild_id)
        locale = await gdb.get('language')
        dropdown = UserMuteSettingsDropDown(locale)
        view = dropdown.get_view()
        await interaction.response.send_message(content=dropdown.content, view=view, ephemeral=True)

    async def process_set_limit(self, interaction: nextcord.Interaction) -> None:
        gdb = GuildDateBases(interaction.guild_id)
        locale = await gdb.get('language')
        modal = LimitSettingsModal(locale)
        await interaction.response.send_modal(modal)

    async def process_change_name(self, interaction: nextcord.Interaction) -> None:
        gdb = GuildDateBases(interaction.guild_id)
        locale = await gdb.get('language')
        modal = NameSettingsModal(locale)
        await interaction.response.send_modal(modal)

    async def process_change_ghost(self, interaction: nextcord.Interaction) -> None:
        gdb = GuildDateBases(interaction.guild_id)
        locale = await gdb.get('language')
        voice = await get_voice(interaction)
        perm = voice.overwrites[interaction.guild.default_role]
        if perm.view_channel:
            perm.view_channel = False
            await voice.set_permissions(interaction.guild.default_role, overwrite=perm)
            await interaction.response.send_message(i18n.t(locale, 'tempvoice.items.func.ghost.success'),
                                                    ephemeral=True)
        else:
            perm.view_channel = True
            await voice.set_permissions(interaction.guild.default_role, overwrite=perm)
            await interaction.response.send_message(i18n.t(locale, 'tempvoice.items.func.unghost.success'),
                                                    ephemeral=True)

    async def process_change_locked(self, interaction: nextcord.Interaction) -> None:
        gdb = GuildDateBases(interaction.guild_id)
        locale = await gdb.get('language')
        voice = await get_voice(interaction)
        perm = voice.overwrites[interaction.guild.default_role]
        if perm.connect:
            perm.connect = False
            await voice.set_permissions(interaction.guild.default_role, overwrite=perm)
            await interaction.response.send_message(i18n.t(locale, 'tempvoice.items.func.lock.success'),
                                                    ephemeral=True)
        else:
            perm.connect = True
            await voice.set_permissions(interaction.guild.default_role, overwrite=perm)
            await interaction.response.send_message(i18n.t(locale, 'tempvoice.items.func.unlock.success'),
                                                    ephemeral=True)

    async def process_set_bitrate(self, interaction: nextcord.Interaction) -> None:
        gdb = GuildDateBases(interaction.guild_id)
        locale = await gdb.get('language')
        modal = BitrateSettingsModal(
            locale, interaction.guild.bitrate_limit//1000)
        await interaction.response.send_modal(modal)

    # next panel
    async def process_invite(self, interaction: nextcord.Interaction) -> None:
        gdb = GuildDateBases(interaction.guild_id)
        locale = await gdb.get('language')
        dropdown = UserInviteSettingsDropDown(locale)
        view = dropdown.get_view()
        await interaction.response.send_message(content=dropdown.content, view=view, ephemeral=True)

    async def process_mute_member_fd(self, interaction: nextcord.Interaction) -> None:
        gdb = GuildDateBases(interaction.guild_id)
        locale = await gdb.get('language')
        dropdown = UserMuteFDSettingsDropDown(locale)
        view = dropdown.get_view()
        await interaction.response.send_message(content=dropdown.content, view=view, ephemeral=True)

    async def process_unmute_member_fd(self, interaction: nextcord.Interaction) -> None:
        gdb = GuildDateBases(interaction.guild_id)
        locale = await gdb.get('language')
        dropdown = UserUnmuteFDSettingsDropDown(locale)
        view = dropdown.get_view()
        await interaction.response.send_message(content=dropdown.content, view=view, ephemeral=True)

    async def process_permit(self, interaction: nextcord.Interaction) -> None:
        gdb = GuildDateBases(interaction.guild_id)
        locale = await gdb.get('language')
        dropdown = UserPermitSettingsDropDown(locale)
        view = dropdown.get_view()
        await interaction.response.send_message(content=dropdown.content, view=view, ephemeral=True)

    async def process_reject(self, interaction: nextcord.Interaction) -> None:
        gdb = GuildDateBases(interaction.guild_id)
        locale = await gdb.get('language')
        dropdown = UserSettingsRejectDropDown(locale)
        view = dropdown.get_view()
        await interaction.response.send_message(content=dropdown.content, view=view, ephemeral=True)

    async def process_ghost(self, interaction: nextcord.Interaction) -> None:
        gdb = GuildDateBases(interaction.guild_id)
        locale = await gdb.get('language')
        voice = await get_voice(interaction)

        perm = voice.overwrites[interaction.guild.default_role]
        perm.view_channel = False

        await voice.set_permissions(interaction.guild.default_role, overwrite=perm)
        await interaction.response.send_message(i18n.t(locale, 'tempvoice.items.func.ghost.success'),
                                                ephemeral=True)

    async def process_unghost(self, interaction: nextcord.Interaction) -> None:
        gdb = GuildDateBases(interaction.guild_id)
        locale = await gdb.get('language')
        voice = await get_voice(interaction)

        perm = voice.overwrites[interaction.guild.default_role]
        perm.view_channel = True

        await voice.set_permissions(interaction.guild.default_role, overwrite=perm)
        await interaction.response.send_message(i18n.t(locale, 'tempvoice.items.func.unghost.success'),
                                                ephemeral=True)

    async def process_lock(self, interaction: nextcord.Interaction) -> None:
        gdb = GuildDateBases(interaction.guild_id)
        locale = await gdb.get('language')
        voice = await get_voice(interaction)

        perm = voice.overwrites[interaction.guild.default_role]
        perm.connect = False

        await voice.set_permissions(interaction.guild.default_role, overwrite=perm)
        await interaction.response.send_message(i18n.t(locale, 'tempvoice.items.func.lock.success'),
                                                ephemeral=True)

    async def process_unlock(self, interaction: nextcord.Interaction) -> None:
        gdb = GuildDateBases(interaction.guild_id)
        locale = await gdb.get('language')
        voice = await get_voice(interaction)

        perm = voice.overwrites[interaction.guild.default_role]
        perm.connect = True

        await voice.set_permissions(interaction.guild.default_role, overwrite=perm)
        await interaction.response.send_message(i18n.t(locale, 'tempvoice.items.func.unlock.success'),
                                                ephemeral=True)
