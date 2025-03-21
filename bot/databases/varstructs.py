from __future__ import annotations


from enum import IntEnum
from typing import (
    TYPE_CHECKING,
    Any,
    Literal,
    NotRequired,
    List,
    Optional,
    TypedDict,
    Dict,
    Tuple,
    Union
)

if TYPE_CHECKING:
    from bot.misc.plugins.logstool import LogType


class GiveawayData(TypedDict):
    guild_id: int
    channel_id: int
    sponsor_id: int
    prize: str
    description: NotRequired[str]
    quantity: int
    date_end: int | float
    types: List[int]
    entries_ids: List[int]
    completed: bool
    winners: NotRequired[List[int]]
    key: str
    token: str


class IdeasMessagesPayload(TypedDict, total=False):
    suggestion: Message
    created: Message

    accept: Message
    accept_with_reason: Message
    approved: Message
    approved_with_reason: Message

    deny: Message
    deny_with_reason: Message
    reject: Message
    reject_with_reason: Message


class IdeasReactionsPayload(TypedDict, total=False):
    success: str
    crossed: str


class IdeasComponentsPayload(TypedDict, total=False):
    suggest: ButtonPayload
    approve: ButtonPayload
    deny: ButtonPayload
    like: ButtonPayload
    dislike: ButtonPayload


class IdeasReactionSystem(IntEnum):
    REACTIONS = 0
    BUTTONS = 1


class IdeasSuggestSystem(IntEnum):
    BUTTONS = 0
    COMMANDS = 1
    EVERYTHING = 2


class IdeasPayload(TypedDict, total=False):
    enabled: bool
    channel_suggest_id: int
    message_suggest_id: int
    channel_offers_id: int
    cooldown: int
    channel_approved_id: int
    channel_denied_id: int
    moderation_role_ids: List[int]
    reaction_system: IdeasReactionSystem
    suggest_system: IdeasSuggestSystem
    revoting: bool
    thread_name: str
    thread_open: bool
    thread_delete: bool
    allow_image: bool
    messages: IdeasMessagesPayload
    reactions: Optional[IdeasReactionsPayload]
    components: IdeasComponentsPayload
    # User id,  moderator_id, reason
    ban_users: List[Tuple[int, int, str]]
    # User id, moderator_id, Timestamp, reason
    muted_users: List[Tuple[int, int, float, str]]


class RoleShopPayload(TypedDict):
    role_id: int
    amount: int
    limit: NotRequired[int]
    name: NotRequired[str]
    description: NotRequired[str]
    using_limit: NotRequired[int]


LogsPayload = Dict[int, List['LogType']]


class ReactionRoleItemPayload(TypedDict):
    reactions: Dict[str, int]
    channel_id: int


ReactionRolePayload = Dict[int, ReactionRoleItemPayload]

Message = Union[str, Dict[str, Any]]


class TicketsMessagesPayload(TypedDict):
    panel: Message
    open: Message
    category: NotRequired[Message]
    controller: Message
    close: Message
    reopen: Message
    delete: Message


class TicketsNamesPayload(TypedDict):
    open: NotRequired[str]
    close: NotRequired[str]


class ButtonPayload(TypedDict, total=False):
    label: str
    emoji: str
    style: Literal[1, 2, 3, 4]


class SelectOptionPayload(TypedDict):
    label: str
    description: NotRequired[str]
    emoji: NotRequired[str]


class TicketsButtonsPayload(TypedDict):
    category_placeholder: str
    modal_placeholder: str
    faq_placeholder: str
    faq_option: SelectOptionPayload
    faq_button_open: ButtonPayload
    faq_button_create: ButtonPayload
    delete_button: ButtonPayload
    reopen_button: ButtonPayload
    close_button: ButtonPayload


class FaqItemPayload(SelectOptionPayload, total=True):
    response: Message


class FaqPayload(TypedDict):
    type: NotRequired[Literal[1, 2]]
    items:  List[FaqItemPayload]


class ModalItemPayload(TypedDict):
    label: str
    style: NotRequired[Literal[1, 2]]
    required: NotRequired[bool]
    placeholder: NotRequired[str]
    default_value: NotRequired[str]
    min_lenght: NotRequired[int]
    max_lenght: NotRequired[int]


class ButtonActionPayload(ButtonPayload, total=True):
    action: str
    data: Any


class PartialCategoryPayload(TypedDict):
    names: TicketsNamesPayload
    messages: TicketsMessagesPayload
    buttons: TicketsButtonsPayload
    actions_buttons: List[ButtonActionPayload]
    type: NotRequired[Literal[1, 2]]
    permissions: NotRequired[Dict[int, Tuple[int, int]]]
    category_id: NotRequired[int]
    closed_category_id: NotRequired[int]
    moderation_roles: NotRequired[List[int]]
    user_closed: NotRequired[bool]
    approved_roles: NotRequired[List[int]]
    saving_history: NotRequired[bool]
    auto_archived: NotRequired[int]
    modals: NotRequired[List[ModalItemPayload]]
    creating_embed_inputs: NotRequired[bool]
    user_tickets_limit: NotRequired[int]


class CategoryPayload(PartialCategoryPayload, ButtonPayload, total=True):
    channel_id: NotRequired[int] = None
    description: NotRequired[str] = None


class TicketsItemPayload(PartialCategoryPayload, total=True):
    channel_id: int
    message_id: int
    enabled: NotRequired[bool]
    faq: NotRequired[FaqPayload]
    category_type: NotRequired[int]
    categories: NotRequired[List[CategoryPayload]]
    global_user_tickets_limit: NotRequired[int]


TicketsPayload = Dict[int, TicketsItemPayload]


class UserTicketPayload(TypedDict):
    owner_id: int
    channel_id: int
    ticket_id: int
    category: CategoryPayload
    inputs: Dict[str, str]
    status: int
    index: int
    messages: NotRequired[List[dict]]


class TempChannelsPayload(TypedDict):
    channel_id: int
    category_id: int
    panel_channel_id: NotRequired[int]
    panel_message_id: NotRequired[int]
    enabled: NotRequired[bool]
    channel_name: NotRequired[str]
    channel_limit: NotRequired[int]
    advance_panel: NotRequired[bool]
    type_panel: NotRequired[int]
    type_message_panel: NotRequired[int]
    removed_mutes:  NotRequired[List[int]]


class TempChannelsItemPayload(TypedDict):
    channel_id: int
    owner_id: int
    status: int
    mutes: NotRequired[Dict[int, bool]]


class TwitchNotifiItemPayload(TypedDict):
    id: str
    channel_id: int
    username: str
    message: str


TwitchNotifiPayload = Dict[str, TwitchNotifiItemPayload]


class YoutubeNotifiItemPayload(TypedDict):
    id: str
    channel_id: int
    yt_name: str
    yt_id: str
    message: str


YoutubeNotifiPayload = Dict[str, YoutubeNotifiItemPayload]


class AutoRolesPayload(TypedDict, total=False):
    every: List[int]
    bot: List[int]
    human: List[int]
