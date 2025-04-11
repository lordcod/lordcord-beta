from __future__ import annotations

from dataclasses import dataclass
import logging
import nextcord
import time

from typing import Dict, List, Literal, Optional, Union, Tuple

import re
import jmespath
import nextcord.state
from bot.misc.plugins import logstool
from bot.misc.time_transformer import display_time
from bot.misc.utils import AsyncSterilization, IdeaPayload, generate_message, get_payload, lord_format

from bot.databases.varstructs import (ButtonPayload, IdeasPayload, IdeasReactionsPayload,
                                      IdeasReactionSystem as ReactionSystemType, IdeasSuggestSystem)
from bot.databases import localdb, GuildDateBases
from bot.languages import i18n
from bot.resources.info import (
    DEFAULT_IDEAS_ALLOW_IMAGE,
    DEFAULT_IDEAS_MAX_LENGTH,
    DEFAULT_IDEAS_MIN_LENGTH,
    DEFAULT_IDEAS_PAYLOAD,
    DEFAULT_IDEAS_PAYLOAD_RU,
    DEFAULT_IDEAS_REVOTING
)


_log = logging.getLogger(__name__)
REGEXP_URL = re.compile(
    r"https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)")
MessageType = Literal['reject', 'deny', 'accept', 'approved']

timeout_data: Dict[int, Dict[int, float]] = {}


@dataclass
class BanData:
    user_id: int
    moderator_id: int
    reason: Optional[str] = None

    @classmethod
    def get(cls, ideas: IdeasPayload, member_id: int) -> Optional[BanData]:
        ban_users = ideas.get('ban_users', [])
        data_ban = jmespath.search(
            f"[?@[0]==`{member_id}`]|[0]", ban_users)
        return data_ban and cls(*data_ban)


@dataclass
class MuteData:
    user_id: int
    moderator_id: int
    timestamp: float
    reason: Optional[str] = None

    @classmethod
    def get(cls, ideas: IdeasPayload, member_id: int) -> Optional[MuteData]:
        muted_users = ideas.get('muted_users', [])
        data_mute = jmespath.search(
            f"[?@[0]==`{member_id}`]|[0]", muted_users)
        return data_mute and cls(*data_mute)


def get_default_payload(locale: str) -> IdeasPayload:
    if locale == 'ru':
        return DEFAULT_IDEAS_PAYLOAD_RU.copy()
    return DEFAULT_IDEAS_PAYLOAD.copy()


def _get_message(type: MessageType, locale: str, payload: dict, reason: str, ideas_data: IdeasPayload):
    DEFAULT_IDEAS_MESSAGES = get_default_payload(locale)['messages']
    if not (
        reason
            and (message_data := ideas_data.get(
                'messages', DEFAULT_IDEAS_MESSAGES).get(type+'_with_reason'))
    ):
        message_data = ideas_data.get(
            'messages', DEFAULT_IDEAS_MESSAGES).get(type)
    return generate_message(lord_format(message_data,
                                        payload))


def get_payload_idea(
    idea_author: nextcord.Member,
    idea_content: Optional[str],
    idea_image: Optional[str],
    promoted_count: Optional[int] = None,
    demoted_count: Optional[int] = None,
    moderator: Optional[nextcord.Member] = None,
    reason: Optional[str] = None
):
    return get_payload(member=idea_author,
                       idea=IdeaPayload(idea_content,
                                        idea_image,
                                        promoted_count,
                                        demoted_count,
                                        moderator,
                                        reason))


class Timeout:
    def __init__(self, guild_id: int, member_id: int) -> None:
        self.guild_id = guild_id
        self.member_id = member_id

    def get(self) -> Optional[float]:
        timeout_data.setdefault(self.guild_id, {})
        return timeout_data[self.guild_id].get(self.member_id)

    def set(self, delay: float) -> None:
        timeout_data.setdefault(self.guild_id, {})
        timeout_data[self.guild_id][self.member_id] = time.time() + delay

    def check_usage(self) -> bool:
        timeout = self.get()
        return timeout and time.time() > timeout


def get_reactions(locale: str, ideas_data: IdeasPayload) -> Tuple[ReactionSystemType, Optional[IdeasReactionsPayload]]:
    DEFAULT_IDEAS_REACTIONS = get_default_payload(locale)['reactions']
    return (ideas_data.get('reaction_system', ReactionSystemType.REACTIONS),
            ideas_data.get('reactions',  DEFAULT_IDEAS_REACTIONS))


def refresh_button(button: nextcord.ui.Button, payload: dict) -> None:
    but_payload = {
        'label': None,
        'emoji': None,
        'style': nextcord.ButtonStyle.gray
    }
    but_payload.update(payload)

    for key, value in but_payload.items():
        setattr(button, key, value)


def refresh_button_with_payload(button: nextcord.ui.Button, button_payload: ButtonPayload, payload: dict) -> None:
    button_data = {}
    for key, value in button_payload.items():
        button_data[key] = lord_format(
            value, payload) if isinstance(value, str) else value
    refresh_button(button, button_data)


def refresh_view(view: Union[ReactionConfirmView.cls, ConfirmView.cls], locale: str, ideas_data: IdeasPayload, payload: dict) -> None:
    DEFAULT_IDEAS_COMPONENTS = get_default_payload(locale)['components']
    components = ideas_data.get('components', DEFAULT_IDEAS_COMPONENTS)

    refresh_button_with_payload(
        view.approve, components.get('approve'), payload)
    refresh_button_with_payload(view.deny, components.get('deny'), payload)
    if isinstance(view, ReactionConfirmView.cls):
        refresh_button_with_payload(
            view.promote, components.get('like'), payload)
        refresh_button_with_payload(
            view.demote, components.get('dislike'), payload)


class VotingModal(nextcord.ui.Modal):
    voting_type: Literal['accept', 'deny']
    locale: str

    async def get_view(self, ideas_data: IdeasPayload, guild: nextcord.Guild):
        type_reaction = ideas_data.get(
            'reaction_system', ReactionSystemType.REACTIONS)
        revoting = ideas_data.get('revoting', DEFAULT_IDEAS_REVOTING)

        if type_reaction == ReactionSystemType.REACTIONS:
            view = await ConfirmView(guild)
        elif type_reaction == ReactionSystemType.BUTTONS:
            view = await ReactionConfirmView(guild)
            view.promote.disabled = True
            view.demote.disabled = True

        if revoting:
            button = view.approve if self.voting_type == 'accept' else view.deny
            button.disabled = True
        else:
            view.approve.disabled = True
            view.deny.disabled = True

        return view

    @staticmethod
    async def process_delete_thread(ideas_data: IdeasPayload, thread: Optional[nextcord.Thread]):
        if ideas_data.get('thread_delete') and thread:
            await thread.delete()

    @staticmethod
    async def process_delete_dnd_message(ideas_data: IdeasPayload, idea_data: dict, _state: nextcord.state.ConnectionState):
        if denrd_msg_id := idea_data.get('denied_message_id'):
            try:
                await _state.http.delete_message(ideas_data['channel_denied_id'], denrd_msg_id)
            except (KeyError, nextcord.NotFound):
                pass

    @staticmethod
    def get_counts(locale: str, msg: nextcord.Message, idea_data: dict, ideas_data: IdeasPayload) -> Tuple[int, int]:
        reaction_type, reactions = get_reactions(locale, ideas_data)
        if reaction_type == ReactionSystemType.REACTIONS:
            rs = nextcord.utils.get(msg.reactions, emoji=reactions['success'])
            promoted = rs.count if rs else 0
            rc = nextcord.utils.get(msg.reactions, emoji=reactions['crossed'])
            demoted = rc.count if rc else 0
        elif reaction_type == ReactionSystemType.BUTTONS:
            promoted = len(idea_data.get('promoted', []))
            demoted = len(idea_data.get('demoted', []))

        return promoted, demoted

    async def callback(self, interaction: nextcord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)

        reason = self.reason.value

        gdb = GuildDateBases(interaction.guild_id)
        ideas_data: IdeasPayload = await gdb.get('ideas')

        mdb = await localdb.get_table('ideas')
        idea_data = await mdb.get(interaction.message.id)
        idea_content, idea_image, idea_author_id = idea_data.get(
            'idea'), idea_data.get('image'), idea_data.get('user_id')
        idea_author = interaction.guild.get_member(idea_author_id)

        payload = get_payload_idea(idea_author, idea_content, idea_image,
                                   *self.get_counts(self.locale, interaction.message, idea_data, ideas_data),
                                   interaction.user, reason)

        await self.process_send_messages(interaction, idea_data, ideas_data, payload, reason)
        if self.voting_type == 'accept':
            await logstool.Logs(interaction.guild).approve_idea(interaction.user, idea_author, idea_content, idea_image, reason)
        elif self.voting_type == 'deny':
            await logstool.Logs(interaction.guild).deny_idea(interaction.user, idea_author, idea_content, idea_image, reason)

        await self.process_delete_thread(ideas_data, interaction.message.thread)
        await self.process_delete_dnd_message(ideas_data, idea_data, interaction._state)


@AsyncSterilization
class ConfirmModal(VotingModal):
    voting_type = 'accept'

    async def __init__(self, guild_id: int):
        gdb = GuildDateBases(guild_id)
        self.locale = locale = await gdb.get('language')

        super().__init__(i18n.t(locale, 'ideas.globals.title'))

        self.reason = nextcord.ui.TextInput(
            label=i18n.t(locale, 'ideas.confirm-modal.reason'),
            required=False,
            style=nextcord.TextInputStyle.paragraph,
            min_length=0,
            max_length=1500,
        )
        self.add_item(self.reason)

    @staticmethod
    def get_accept_message(payload: dict, locale: str, reason: str, ideas_data: IdeasPayload):
        return _get_message('accept', locale, payload, reason, ideas_data)

    @staticmethod
    def get_approved_message(payload: dict, locale: str, reason: str, ideas_data: IdeasPayload):
        return _get_message('approved', locale, payload, reason, ideas_data)

    async def process_send_messages(
        self,
        interaction: nextcord.Interaction,
        idea_data: IdeaPayload,
        ideas_data: IdeasPayload,
        payload: dict,
        reason: str
    ):
        approved_channel_id = ideas_data.get('channel_approved_id')
        approved_channel = interaction.guild.get_channel(approved_channel_id)

        accept_message = self.get_accept_message(
            payload, self.locale, reason, ideas_data)
        view = await self.get_view(ideas_data, interaction.guild)
        await interaction.message.edit(**accept_message, view=view)

        if approved_channel is None:
            return

        approved_message = self.get_approved_message(
            payload, self.locale, reason, ideas_data)
        apprd_msg = await approved_channel.send(**approved_message)

        idea_data['approved_message_id'] = apprd_msg.id

        mdb = await localdb.get_table('ideas')
        await mdb.set(interaction.message.id, idea_data)


@AsyncSterilization
class DenyModal(VotingModal):
    voting_type = 'deny'

    async def __init__(self, guild_id: int) -> None:
        gdb = GuildDateBases(guild_id)
        self.locale = locale = await gdb.get('language')

        super().__init__(i18n.t(locale, 'ideas.globals.title'))

        self.reason = nextcord.ui.TextInput(
            label=i18n.t(locale, 'ideas.confirm-modal.reason'),
            required=False,
            style=nextcord.TextInputStyle.paragraph,
            min_length=0,
            max_length=1500,
        )
        self.add_item(self.reason)

    @staticmethod
    def get_deny_message(payload: dict, locale: str, reason: str, ideas_data: IdeasPayload):
        return _get_message('deny', locale, payload, reason, ideas_data)

    @staticmethod
    def get_reject_message(payload: dict, locale: str, reason: str, ideas_data: IdeasPayload):
        return _get_message('reject', locale, payload, reason, ideas_data)

    async def process_send_messages(
        self,
        interaction: nextcord.Interaction,
        idea_data: IdeaPayload,
        ideas_data: IdeasPayload,
        payload: dict,
        reason: str
    ):
        channel_denied_id = ideas_data.get('channel_denied_id')
        channel_denied = interaction.guild.get_channel(channel_denied_id)

        deny_message = self.get_deny_message(
            payload, self.locale, reason, ideas_data)
        view = await self.get_view(ideas_data, interaction.guild)
        await interaction.message.edit(**deny_message, view=view)

        if channel_denied is None:
            return

        reject_message = self.get_reject_message(
            payload, self.locale,  reason, ideas_data)
        denrd_msg = await channel_denied.send(**reject_message)

        idea_data['denied_message_id'] = denrd_msg.id

        mdb = await localdb.get_table('ideas')
        await mdb.set(interaction.message.id, idea_data)


@AsyncSterilization
class ConfirmView(nextcord.ui.View):
    async def __init__(self, guild: Optional[nextcord.Guild] = None):
        super().__init__(timeout=None)

        if guild is None:
            return

        gdb = GuildDateBases(guild.id)
        locale = await gdb.get('language')
        ideas_data: IdeasPayload = await gdb.get('ideas')

        if IdeasSuggestSystem.COMMANDS == ideas_data.get('suggest_system'):
            self.remove_item(self.approve)
            self.remove_item(self.deny)

        refresh_view(self, locale,  ideas_data, get_payload(guild=guild))

    async def interaction_check(self, interaction: nextcord.Interaction) -> bool:
        gdb = GuildDateBases(interaction.guild_id)
        locale = await gdb.get('language')

        ideas_data: IdeasPayload = await gdb.get('ideas')
        enabled: bool = ideas_data.get('enabled')

        moderation_role_ids = ideas_data.get('moderation_role_ids', [])
        role_ids = set(interaction.user._roles)
        moderation_roles = set(moderation_role_ids)

        if not enabled:
            await interaction.response.send_message(i18n.t(
                locale, 'ideas.globals.ideas_disabled'), ephemeral=True)
            return False

        if not role_ids & moderation_roles and not interaction.user.guild_permissions.administrator:
            await interaction.response.defer(ephemeral=True)
            return False

        return True

    @nextcord.ui.button(label="Approve",
                        style=nextcord.ButtonStyle.green,
                        custom_id='ideas-confirm:confirm')
    async def approve(self,
                      button: nextcord.ui.Button,
                      interaction: nextcord.Interaction):
        modal = await ConfirmModal(interaction.guild_id)
        await interaction.response.send_modal(modal)

    @nextcord.ui.button(label="Deny",
                        style=nextcord.ButtonStyle.red,
                        custom_id='ideas-confirm:cancel')
    async def deny(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        modal = await DenyModal(interaction.guild_id)
        await interaction.response.send_modal(modal)


@AsyncSterilization
class ReactionConfirmView(nextcord.ui.View):
    promoted_data: List[int]
    demoted_data: List[int]

    async def __init__(self, guild: Optional[nextcord.Guild] = None):
        super().__init__(timeout=None)

        if guild is None:
            return

        gdb = GuildDateBases(guild.id)
        self.locale = await gdb.get('language')
        ideas_data: IdeasPayload = await gdb.get('ideas')

        if IdeasSuggestSystem.COMMANDS == ideas_data.get('suggest_system'):
            self.remove_item(self.approve)
            self.remove_item(self.deny)

        payload = get_payload(guild=guild)
        payload['idea.promotedCount'] = payload['idea.demotedCount'] = 0
        refresh_view(self, self.locale, ideas_data, payload)

    async def interaction_check(self, interaction: nextcord.Interaction) -> bool:
        custom_id = interaction.data['custom_id']
        if custom_id.startswith("reactions-ideas-confirm:"):
            return True
        return await ConfirmView.cls.interaction_check(self, interaction)

    def change_votes(self, ideas_data: IdeasPayload, payload: dict) -> None:
        refresh_view(self, self.locale, ideas_data, payload)

    async def save_data(self, message_id) -> None:
        mdb = await localdb.get_table('ideas')
        idea_data = await mdb.get(message_id)
        idea_data.update({
            'promoted': self.promoted_data,
            'demoted': self.demoted_data
        })
        await mdb.set(message_id, idea_data)

    async def load_data(self, guild_id: int, message_id: int) -> None:
        gdb = GuildDateBases(guild_id)
        self.locale = await gdb.get('language')

        mdb = await localdb.get_table('ideas')
        idea_data = await mdb.get(message_id)
        self.promoted_data = idea_data.get('promoted', [])
        self.demoted_data = idea_data.get('demoted', [])

    @nextcord.ui.button(label="0", emoji="👍", row=1, custom_id="reactions-ideas-confirm:promote")
    async def promote(self, button: nextcord.ui.Button,
                      interaction: nextcord.Interaction):
        await interaction.response.defer()
        await self.load_data(interaction.guild_id, interaction.message.id)

        gdb = GuildDateBases(interaction.guild.id)
        ideas_data: IdeasPayload = await gdb.get('ideas')

        if interaction.user.id in self.promoted_data:
            self.promoted_data.remove(interaction.user.id)
        elif interaction.user.id in self.demoted_data:
            self.demoted_data.remove(interaction.user.id)
            self.promoted_data.append(interaction.user.id)
        else:
            self.promoted_data.append(interaction.user.id)

        payload = get_payload_idea(interaction.user, None, None, len(
            self.promoted_data), len(self.demoted_data))
        self.change_votes(ideas_data, payload)

        await self.save_data(interaction.message.id)
        await interaction.message.edit(view=self)

    @nextcord.ui.button(label="0", emoji="👎", row=1, custom_id="reactions-ideas-confirm:demote")
    async def demote(self, button: nextcord.ui.Button,
                     interaction: nextcord.Interaction):
        await interaction.response.defer()
        await self.load_data(interaction.guild_id, interaction.message.id)

        gdb = GuildDateBases(interaction.guild.id)
        ideas_data: IdeasPayload = await gdb.get('ideas')

        if interaction.user.id in self.demoted_data:
            self.demoted_data.remove(interaction.user.id)
        elif interaction.user.id in self.promoted_data:
            self.promoted_data.remove(interaction.user.id)
            self.demoted_data.append(interaction.user.id)
        else:
            self.demoted_data.append(interaction.user.id)

        payload = get_payload_idea(interaction.user, None, None, len(
            self.promoted_data), len(self.demoted_data))
        self.change_votes(ideas_data, payload)

        await self.save_data(interaction.message.id)
        await interaction.message.edit(view=self)

    @nextcord.ui.button(label="Approve",
                        style=nextcord.ButtonStyle.green,
                        custom_id='ideas-confirm:confirm',
                        row=0)
    async def approve(self,
                      button: nextcord.ui.Button,
                      interaction: nextcord.Interaction):
        modal = await ConfirmModal(interaction.guild_id)
        await interaction.response.send_modal(modal)

    @nextcord.ui.button(label="Deny",
                        style=nextcord.ButtonStyle.red,
                        custom_id='ideas-confirm:cancel',
                        row=0)
    async def deny(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        modal = await DenyModal(interaction.guild_id)
        await interaction.response.send_modal(modal)


@AsyncSterilization
class IdeaModal(nextcord.ui.Modal):
    async def __init__(self, guild_id: int):
        gdb = GuildDateBases(guild_id)
        self.locale = locale = await gdb.get('language')
        ideas_data: IdeasPayload = await gdb.get('ideas')
        allow_image = ideas_data.get('allow_image', DEFAULT_IDEAS_ALLOW_IMAGE)

        super().__init__(i18n.t(locale, 'ideas.globals.title'))

        self.idea = nextcord.ui.TextInput(
            label=i18n.t(locale, 'ideas.idea-modal.label'),
            style=nextcord.TextInputStyle.paragraph,
            placeholder=i18n.t(locale, 'ideas.idea-modal.placeholder'),
            min_length=ideas_data.get('min_length', DEFAULT_IDEAS_MIN_LENGTH),
            max_length=ideas_data.get('max_length', DEFAULT_IDEAS_MAX_LENGTH)
        )
        self.add_item(self.idea)

        self.image = nextcord.ui.TextInput(
            label=i18n.t(locale, 'ideas.idea-modal.image.label'),
            style=nextcord.TextInputStyle.short,
            placeholder=i18n.t(locale, 'ideas.idea-modal.image.placeholder'),
            min_length=10,
            max_length=250,
            required=False
        )
        if allow_image:
            self.add_item(self.image)

    @staticmethod
    async def get_message(
        locale: str,
        ideas_data: IdeasPayload,
        channel: nextcord.TextChannel,
        created_message: dict
    ) -> nextcord.Message:
        reaction_type, reactions = get_reactions(locale, ideas_data)

        if reaction_type == ReactionSystemType.REACTIONS:
            view = await ConfirmView(channel.guild)
            mes = await channel.send(**created_message, view=view)
            if reactions is not None:
                if success := reactions.get('success'):
                    await mes.add_reaction(success)
                if crossed := reactions.get('crossed'):
                    await mes.add_reaction(crossed)

        if reaction_type == ReactionSystemType.BUTTONS:
            view = await ReactionConfirmView(channel.guild)
            mes = await channel.send(**created_message, view=view)

        return mes

    @staticmethod
    async def create_thread(locale: str, message: nextcord.Message, ideas_data: IdeasPayload, payload: dict) -> None:
        if not ideas_data.get('thread_open'):
            return

        DEFAULT_THREAD_NAME = get_default_payload(locale)['thread_name']
        thread_name = ideas_data.get('thread_name', DEFAULT_THREAD_NAME)
        await message.create_thread(name=lord_format(thread_name,
                                                     payload))

    async def callback(self, interaction: nextcord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)

        gdb = GuildDateBases(interaction.guild_id)
        ideas_data: IdeasPayload = await gdb.get('ideas')
        channel_offers_id = ideas_data.get('channel_offers_id')
        cooldown = ideas_data.get('cooldown', 0)

        channel = interaction.guild.get_channel(channel_offers_id)
        idea = self.idea.value
        image = self.image.value

        if not (image and REGEXP_URL.fullmatch(image)):
            image = None

        payload = get_payload_idea(interaction.user, idea, image)

        DEFAULT_IDEAS_MESSAGES = get_default_payload(self.locale)['messages']
        created_message_data = ideas_data.get(
            'messages', DEFAULT_IDEAS_MESSAGES).get('created')
        created_message = generate_message(lord_format(created_message_data,
                                                       payload))

        mes = await self.get_message(self.locale, ideas_data, channel, created_message)
        await self.create_thread(self.locale, mes, ideas_data, payload)

        idea_data = {
            'user_id': interaction.user.id,
            'idea': idea,
            'image': image
        }
        mdb = await localdb.get_table('ideas')
        await mdb.set(mes.id, idea_data)

        Timeout(interaction.guild_id,
                interaction.user.id).set(cooldown)
        await logstool.Logs(interaction.guild).create_idea(interaction.user, idea, image)


@AsyncSterilization
class IdeaView(nextcord.ui.View):
    async def __init__(self, guild: Optional[nextcord.Guild] = None):
        super().__init__(timeout=None)

        if guild is None:
            return

        gdb = GuildDateBases(guild.id)
        ideas_data: IdeasPayload = await gdb.get('ideas')
        locale = await gdb.get('language')

        DEFAULT_IDEAS_COMPONENTS = get_default_payload(locale)['components']
        components = ideas_data.get('components', DEFAULT_IDEAS_COMPONENTS)

        refresh_button_with_payload(self.suggest, components.get(
            'suggest'), get_payload(guild=guild))

    @nextcord.ui.button(
        label="Suggest an idea",
        style=nextcord.ButtonStyle.green,
        custom_id="ideas-main-button:suggest"
    )
    async def suggest(
        self,
        button: nextcord.ui.Button,
        interaction: nextcord.Interaction
    ) -> None:
        gdb = GuildDateBases(interaction.guild_id)
        locale = await gdb.get('language')
        ideas_data: IdeasPayload = await gdb.get('ideas')
        cooldown: int = ideas_data.get('cooldown', 0)
        enabled: bool = ideas_data.get('enabled', False)
        ban_data = BanData.get(ideas_data, interaction.user.id)
        mute_data = MuteData.get(ideas_data, interaction.user.id)
        user_timeout = Timeout(interaction.guild_id, interaction.user.id).get()

        if not enabled:
            await interaction.response.send_message(i18n.t(locale, 'ideas.globals.ideas-disabled'), ephemeral=True)
            return

        if user_timeout and user_timeout > time.time():
            await interaction.response.send_message(
                content=i18n.t(
                    locale, 'ideas.idea-view.timeout-message',
                    time=int(user_timeout),
                    every_time=display_time(cooldown, locale)
                ),
                ephemeral=True
            )
            return

        if ban_data is not None:
            moderator = interaction.guild.get_member(ban_data.moderator_id)
            await interaction.response.send_message(i18n.t(locale, 'ideas.mod.permission.ban',
                                                           moderator=moderator.mention,
                                                           reason=ban_data.reason or 'unspecified'),
                                                    ephemeral=True)
            return

        if mute_data is not None:
            moderator = interaction.guild.get_member(mute_data.moderator_id)
            await interaction.response.send_message(i18n.t(locale, 'ideas.mod.permission.mute',
                                                           time=mute_data.timestamp,
                                                           display_time=display_time(
                                                               mute_data.timestamp-time.time()),
                                                           moderator=moderator.mention,
                                                           reason=mute_data.reason or 'unspecified'),
                                                    ephemeral=True)
            return

        modal = await IdeaModal(interaction.guild_id)
        await interaction.response.send_modal(modal)
