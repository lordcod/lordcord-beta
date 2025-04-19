from datetime import datetime
import inspect
from typing import Optional, Dict, Any, Union, List, Tuple, Iterable, TYPE_CHECKING

import nextcord

from bot.databases import GuildDateBases
from bot.databases.varstructs import CategoryPayload

from .misc import MISSING
from bot.resources.info import Emoji

if TYPE_CHECKING:
    from bot.misc.noti.twitch.noti import Stream as TwStream, User as TwUser
    from bot.misc.noti.youtube.noti import Video as YtVideo

from collections import namedtuple

WelMes = namedtuple("WelcomeMessageItem", ["name", "link", "description"])

welcome_message_items = {
    "None": WelMes("None", None, None),
    "my-image": WelMes("My image", ..., "You will be able to enter a link to an image."),
    "view-from-mountain": WelMes("View from mountain", "https://i.postimg.cc/Hnpz0ycb/view-from-mountain.jpg", "Summer vibes, mountain views, sunset - all adds charm."),
    "autumn-street": WelMes("Autumn street", "https://i.postimg.cc/sXnQ8QHY/autumn-street.jpg", "The joy of a bright autumn morning, surrounded by a stunning building and the atmosphere of autumn."),
    "winter-day": WelMes("Winter day", "https://i.postimg.cc/qBhyYQ0g/winter-day.jpg", "Dazzling winter day, majestic mountain, small buildings, sparkling highway, snow-white covers."),
    "magic-city": WelMes("Magic city", "https://i.postimg.cc/hjJzk4kN/magic-city.jpg", "The beautiful atmosphere and scenic views from the boat."),
    "city-dawn": WelMes("City dawn", "https://i.postimg.cc/13J84NPL/city-dawn.jpg", "Starry sky, breeze, rustling leaves, crickets, fireflies, bonfire - perfect night.")
}


def parse_prefix(
    prefix: str,
    iterable: Union[Iterable[Tuple[Union[str, int], Any]],
                    Dict[Union[str, int], Any],
                    List[Any]]
) -> Dict[str, Any]:
    if isinstance(iterable, dict):
        iterable = iterable.items()
    if isinstance(iterable, list):
        iterable = enumerate(iterable)

    ret = {}
    for key, value in iterable:
        if isinstance(value, (dict, list)):
            ret.update(parse_prefix(f'{prefix}.{key}', value))
            continue
        ret[f'{prefix}.{key}'] = value
    return ret


class TempletePayload:
    _prefix: Optional[str] = MISSING
    _as_prefix: bool = False

    def _get_prefix(self, prefix: Optional[str], name: str) -> str:
        return f"{prefix}.{name}" if prefix else name

    def _to_dict(self):
        prefix = self._prefix if self._prefix is not MISSING else self.__class__.__name__
        base = {}

        if self._as_prefix:
            base[prefix] = str(self)

        for name, arg in inspect.getmembers(self):
            if name.startswith("_"):
                continue

            self_prefix = self._get_prefix(prefix, name)
            if isinstance(arg, dict):
                base.update(parse_prefix(self_prefix, arg))
                continue

            base[self_prefix] = arg

        return base


class StreamPayload(TempletePayload):
    _prefix = 'stream'

    def __init__(self, stream: 'TwStream', user: 'TwUser') -> None:
        self.username = stream.user_name
        self.title = stream.title
        self.gameName = stream.game_name
        self.thumbnailUrl = stream.thumbnail_url
        self.avatarUrl = user.profile_image_url
        self.url = stream.url


class VideoPayload(TempletePayload):
    _prefix = 'video'

    def __init__(self, video: 'YtVideo') -> None:
        self.username = video.channel.name
        self.title = video.title
        self.description = video.description
        self.url = video.url
        self.videoIcon = video.thumbnail.url


class GuildPayload(TempletePayload):
    _prefix = 'guild'
    _as_prefix = True

    def __init__(self, guild: nextcord.Guild) -> None:
        gdb = GuildDateBases(guild.id)

        self.color: int = gdb.get_cache('color')
        self.id: int = guild.id
        self.name: str = guild.name
        self.memberCount: int = guild.member_count
        self.createdAt: int = guild.created_at.timestamp()
        self.createdDt: str = guild.created_at.isoformat()
        self.premiumSubscriptionCount: int = guild.premium_subscription_count

        self.icon = guild.icon.url if guild.icon and guild.icon.url else None

    def __str__(self) -> str:
        return self.name


class MemberPayload(TempletePayload):
    _prefix = 'member'
    _as_prefix = True

    def __init__(self, member: nextcord.Member) -> None:
        self.id: int = member.id
        self.mention: str = member.mention
        self.username: str = member.name
        self.name: str = member.name
        self.displayName: str = member.display_name
        self.discriminator: str = member.discriminator
        self.tag = f'{member.name}#{member.discriminator}'
        self.avatar = member.display_avatar.url

    def __str__(self) -> str:
        return self.mention


class IdeaPayload(TempletePayload):
    _prefix = 'idea'

    def __init__(
        self,
        content: str,
        image: Optional[str],
        promoted_count: Optional[int] = None,
        demoted_count: Optional[int] = None,
        moderator: Optional[nextcord.Member] = None,
        reason: Optional[str] = None,
    ) -> None:
        self.content = content
        self.image = image
        self.reason = reason
        self.promotedCount = promoted_count
        self.demotedCount = demoted_count

        if moderator is not None:
            mod = MemberPayload(moderator)
            mod._prefix = None
            self.mod = mod._to_dict()


def get_payload(
    *,
    member: Optional[Union[nextcord.Member, nextcord.User]] = None,
    guild: Optional[nextcord.Guild] = None,
    stream: Optional['TwStream'] = None,
    user: Optional['TwUser'] = None,
    video: Optional['YtVideo'] = None,
    category: Optional[CategoryPayload] = None,
    inputs: Optional[Dict[str, str]] = None,
    ticket_count: Optional[dict] = None,
    voice_count: Optional[dict] = None,
    idea: Optional[IdeaPayload] = None
) -> dict:
    bot_payload = None
    if guild is None and isinstance(member, nextcord.Member):
        guild = member.guild
    if guild is not None:
        bot = guild._state.user
        bot_payload = MemberPayload(bot)
        bot_payload._prefix = 'bot'

    data = {
        'today_dt': datetime.today().isoformat()
    }
    if member is not None:
        data.update(MemberPayload(member)._to_dict())
    if guild is not None:
        data.update(GuildPayload(guild)._to_dict())
    if stream and user:
        data.update(StreamPayload(stream, user)._to_dict())
    if video:
        data.update(VideoPayload(video)._to_dict())
    if bot_payload:
        data.update(bot_payload._to_dict())
    if idea:
        data.update(idea._to_dict())
    if voice_count:
        data.update(parse_prefix('voice.count', voice_count))
    if inputs:
        data.update(parse_prefix('ticket.forms', list(inputs.values())))
    if ticket_count:
        data.update(parse_prefix('ticket.count', ticket_count))
    if category:
        data['ticket.category.name'] = category['label']

    return data
