from __future__ import annotations
import contextlib
import getopt
import logging
import nextcord
from nextcord.ext import commands


import inspect
import nextcord.types
import nextcord.types.message
import regex
import string
import random
import aiohttp
import asyncio
import time
import emoji
import orjson
import argparse

from asyncio import TimerHandle
from collections import namedtuple
from typing import (TYPE_CHECKING, Callable,  Coroutine, Dict, Generic,  Optional,  Tuple,  Union,
                    Any, Iterable,  Self, List, TypeVar, overload)
from datetime import datetime
from captcha.image import ImageCaptcha
from io import BytesIO
from functools import lru_cache
from dataclasses import dataclass, field
from PIL import Image, ImageDraw, ImageFont
from easy_pil import Editor, Font, load_image_async

from bot.databases import GuildDateBases
from cryptography.fernet import Fernet
from bot.databases.varstructs import CategoryPayload
from bot.resources import ether
from bot.resources.ether import Emoji
from functools import partial
import numpy as np
from colormath.color_objects import sRGBColor, LabColor
from colormath.color_conversions import convert_color
from colormath.color_diff import delta_e_cie2000

if TYPE_CHECKING:
    from bot.misc.lordbot import LordBot
    from bot.misc.noti.twnoti import Stream as TwStream, User as TwUser
    from bot.misc.noti.ytnoti import Video as YtVideo

_log = logging.getLogger(__name__)
T = TypeVar('T')
C_co = TypeVar("C_co", bound=type, covariant=True)
WelMes = namedtuple("WelcomeMessageItem", ["name", "link", "description"])

REGEXP_FORMAT = regex.compile(r"(\{\s*([\.\|\s\-_a-zA-Z0-9]*)\s*\})")
MISSING = nextcord.utils._MissingSentinel()


welcome_message_items = {
    "None": WelMes("None", None, None),
    "my-image": WelMes("My image", ..., "You will be able to enter a link to an image."),
    "view-from-mountain": WelMes("View from mountain", "https://i.postimg.cc/Hnpz0ycb/view-from-mountain.jpg", "Summer vibes, mountain views, sunset - all adds charm."),
    "autumn-street": WelMes("Autumn street", "https://i.postimg.cc/sXnQ8QHY/autumn-street.jpg", "The joy of a bright autumn morning, surrounded by a stunning building and the atmosphere of autumn."),
    "winter-day": WelMes("Winter day", "https://i.postimg.cc/qBhyYQ0g/winter-day.jpg", "Dazzling winter day, majestic mountain, small buildings, sparkling highway, snow-white covers."),
    "magic-city": WelMes("Magic city", "https://i.postimg.cc/hjJzk4kN/magic-city.jpg", "The beautiful atmosphere and scenic views from the boat."),
    "city-dawn": WelMes("City dawn", "https://i.postimg.cc/13J84NPL/city-dawn.jpg", "Starry sky, breeze, rustling leaves, crickets, fireflies, bonfire - perfect night.")
}

hex_int = partial(int, base=16)


def patch_asscalar(a):
    return a.item()


setattr(np, "asscalar", patch_asscalar)


colors = {
    '#58b99d': '<:lzelrole:1265262139266826332>',
    '#3a7e6b': '<:dzelrole:1265262043385036852>',
    '#65c97a': '<:lsalrole:1265262146481295463>',
    '#448952': '<:dsalrole:1265262039111041054>',
    '#5296d5': '<:lgolrole:1265262047931924580>',
    '#356590': '<:dgolrole:1265262030693072967>',
    '#925cb1': '<:lfiorole:1265262140697083905>',
    '#693986': '<:dfiorole:1265262029271203980>',
    '#d63864': '<:lmalrole:1265262051463401482>',
    '#9f2756': '<:dmalrole:1265262034014961714>',
    '#eac644': '<:ljolrole:1265262142098243720>',
    '#b87f2e': '<:djolrole:1265262032299757630>',
    '#d8833a': '<:lorarole:1265262144702779463>',
    '#9c491a': '<:dorarole:1265262035399213056>',
    '#d65745': '<:lredrole:1265262054772707452>',
    '#8d3528': '<:dredrole:1265262037060030578>',
    '#98a5a6': '<:lserrole:1265262058639851602>',
    '#989c9f': '<:dserrole:1265262040432513054>',
    '#667c89': '<:ltserole:1265262061399707738>',
    '#596d79': '<:dtserole:1265262041921486912>'
}


class TempletePayload:
    _prefix: Optional[str] = MISSING
    _as_prefix: bool = False

    def _get_prefix(self, prefix: Optional[str], name: str) -> str:
        return (f"{prefix}.{name}"
                if prefix else name)

    def _to_dict(self):
        if self._prefix is not MISSING:
            prefix = self._prefix
        else:
            prefix = self.__class__.__name__

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

    def __init__(self, stream: TwStream, user: TwUser) -> None:
        self.username = stream.user_name
        self.title = stream.title
        self.gameName = stream.game_name
        self.thumbnailUrl = stream.thumbnail_url
        self.avatarUrl = user.profile_image_url
        self.url = stream.url


class VideoPayload(TempletePayload):
    _prefix = 'video'

    def __init__(self, video: YtVideo) -> None:
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

        self.color: int = gdb.get_hash('color')
        self.id: int = guild.id
        self.name: str = guild.name
        self.memberCount: int = guild.member_count
        self.createdAt: int = guild.created_at.timestamp()
        self.createdDt: str = guild.created_at.isoformat()
        self.premiumSubscriptionCount: int = guild.premium_subscription_count

        if not (guild.icon and guild.icon.url):
            self.icon = None
        else:
            self.icon: str = guild.icon.url

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
    _as_prefix = False

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


def get_payload(
    *,
    member: Optional[Union[nextcord.Member, nextcord.User]] = None,
    guild: Optional[nextcord.Guild] = None,
    stream: Optional[TwStream] = None,
    user: Optional[TwUser] = None,
    video: Optional[YtVideo] = None,
    category: Optional[CategoryPayload] = None,
    inputs: Optional[Dict[str, str]] = None,
    ticket_count: Optional[dict] = None,
    voice_count: Optional[dict] = None,
    idea: Optional[IdeaPayload] = None
) -> dict:
    bot_payload = None
    if guild is None and member is not None and isinstance(member, nextcord.Member):
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
    if stream is not None and user is not None:
        data.update(StreamPayload(stream, user)._to_dict())
    if video is not None:
        data.update(VideoPayload(video)._to_dict())
    if bot_payload is not None:
        data.update(bot_payload._to_dict())
    if idea is not None:
        data.update(idea._to_dict())
    if voice_count is not None:
        data.update(parse_prefix('voice.count', voice_count))
    if inputs is not None and inputs:
        data.update(parse_prefix('ticket.forms', list(inputs.values())))
    if ticket_count is not None:
        data.update(parse_prefix('ticket.count', ticket_count))
    if category is not None and category:
        data['ticket.category.name'] = category['label']

    return data


class Tokenizer:
    @staticmethod
    def encrypt(message: bytes, key: bytes) -> bytes:
        return Fernet(key).encrypt(message)

    @staticmethod
    def decrypt(token: bytes, key: bytes) -> bytes:
        return Fernet(key).decrypt(token)

    @staticmethod
    def generate_key() -> bytes:
        return Fernet.generate_key()


_blackjack_games = {}


class BlackjackGame:
    cards: Dict[str, Optional[int]] = {
        '<:hearts_of_ace:1236254919347142688>': None, '<:hearts_of_two:1236254940016545843>': 2, '<:hearts_of_three:1236254938158338088>': 3, '<:hearts_of_four:1236254924757536799>': 4, '<:hearts_of_five:1236254923050586212>': 5, '<:hearts_of_six:1236254934920593438>': 6, '<:hearts_of_seven:1236254933309718641>': 7, '<:hearts_of_eight:1236254921272066078>': 8, '<:hearts_of_nine:1236254929803280394>': 9, '<:hearts_of_ten:1236254936514428948>': 10, '<:hearts_of_jack:1236254926263418932>': 10, '<:hearts_of_queen:1236254931464228905>': 10, '<:hearts_of_king:1236254928104587336>': 10,
        '<:spades_of_ace:1236254941820092506>': None, '<:spades_of_two:1236256183048863836>': 2, '<:spades_of_three:1236256162933112862>': 3, '<:spades_of_four:1236254946454667325>': 4, '<:spades_of_five:1236256181433929768>': 5, '<:spades_of_six:1236256158835277846>': 6, '<:spades_of_seven:1236256156834594836>': 7, '<:spades_of_eight:1236254943632162857>': 8, '<:spades_of_nine:1236254952901316659>': 9, '<:spades_of_ten:1236256161024708619>': 10, '<:spades_of_jack:1236254949072048200>': 10, '<:spades_of_queen:1236254955099262996>': 10, '<:spades_of_king:1236254951001292840>': 10,
        '<:clubs_of_ace:1236254878867918881>': None, '<:clubs_of_two:1236254897243029607>': 2, '<:clubs_of_three:1236254896026812508>': 3, '<:clubs_of_four:1236254884232167474>': 4, '<:clubs_of_five:1236254882533740614>': 5, '<:clubs_of_six:1236254893015175220>': 6, '<:clubs_of_seven:1236254891572334644>': 7, '<:clubs_of_eight:1236254880981586021>': 8, '<:clubs_of_nine:1236254888833581116>': 9, '<:clubs_of_ten:1236254894525120522>': 10, '<:clubs_of_jack:1236254886119739423>': 10, '<:clubs_of_queen:1236254890234347540>': 10, '<:clubs_of_king:1236254887474368533>': 10,
        '<:diamonds_of_ace:1236254898799247441>': None, '<:diamonds_of_two:1236254917266636912>': 2, '<:diamonds_of_three:1236254916394225696>': 3, '<:diamonds_of_four:1236254903140220988>': 4, '<:diamonds_of_five:1236254901835661333>': 5, '<:diamonds_of_six:1236254913412202496>': 6, '<:diamonds_of_seven:1236254911797268500>': 7, '<:diamonds_of_eight:1236254900338430042>': 8, '<:diamonds_of_nine:1236254908164870164>': 9, '<:diamonds_of_ten:1236254914867626064>': 10, '<:diamonds_of_jack:1236254904931061800>': 10, '<:diamonds_of_queen:1236254909813358602>': 10, '<:diamonds_of_king:1236254906562777191>': 10
    }

    def __init__(self, member: nextcord.Member, amount: int) -> None:
        if _blackjack_games.get(f'{member.guild.id}:{member.id}'):
            raise TypeError('Game is started')

        _blackjack_games[f'{member.guild.id}:{member.id}'] = self
        self.member = member
        self.amount = amount

        self.cards = self.cards.copy()
        self.your_cards = [self.get_random_cart() for _ in range(2)]
        self.dealer_cards = [self.get_random_cart() for _ in range(2)]

        self.gid = randquan(9)

    @property
    def your_value(self) -> int:
        return self.calculate_result(self.your_cards)

    @property
    def dealer_value(self) -> int:
        return self.calculate_result(self.dealer_cards)

    async def completed_embed(self) -> nextcord.Embed:
        gdb = GuildDateBases(self.member.guild.id)
        color = await gdb.get('color')

        embed = nextcord.Embed(
            title="Blackjack",
            description=f"Result: {await self.get_winner_title()}",
            color=color
        )
        embed.add_field(
            name="Your Hand",
            value=(
                f"{' '.join(self.your_cards)}\n\n"
                f"Value: {self.your_value}"
            )
        )
        embed.add_field(
            name="Dealer Hand",
            value=(
                f"{' '.join(self.dealer_cards)}\n\n"
                f"Value: {self.dealer_value}"
            )
        )
        return embed

    async def embed(self) -> nextcord.Embed:
        gdb = GuildDateBases(self.member.guild.id)
        color = await gdb.get('color')
        economic_settings: dict = await gdb.get('economic_settings')
        currency_emoji = economic_settings.get('emoji')

        embed = nextcord.Embed(
            title="Blackjack",
            description=f"Bet: {self.amount}{currency_emoji}",
            color=color
        )
        embed.add_field(
            name="Your Hand",
            value=(
                f"{' '.join(self.your_cards)}\n\n"
                f"Value: {self.your_value}"
            )
        )
        embed.add_field(
            name="Dealer Hand",
            value=(
                f"{self.dealer_cards[0]} {Emoji.empty_card}\n\n"
                f"Value: {self.calculate_result(self.dealer_cards[0:1])}"
            )
        )
        return embed

    def is_avid_winner(self) -> Optional[int]:
        if (self.your_value == 21
                and self.dealer_value == 21
                and 2 == len(self.your_cards)
                and 2 == len(self.dealer_cards)):
            return 2
        elif self.your_value == 21 and 2 == len(self.your_cards):
            return 1
        elif self.dealer_value == 21 and 2 == len(self.dealer_cards):
            return 0
        return None

    def is_winner(self) -> int:
        if self.is_exceeds_dealer():
            return 1
        if self.is_exceeds_your():
            return 0

        if self.your_value == self.dealer_value:
            return 2
        if self.your_value > self.dealer_value:
            return 1
        if self.dealer_value > self.your_value:
            return 0

    async def get_winner_title(self) -> int:
        gdb = GuildDateBases(self.member.guild.id)
        economic_settings: dict = await gdb.get('economic_settings')
        currency_emoji = economic_settings.get('emoji')

        match self.is_winner():
            case 2:
                return f"Draw {self.amount :,}{currency_emoji}"
            case 1:
                return f"Won {1.5*self.amount :,.0f}{currency_emoji}" if self.is_avid_winner() == 1 else f"Won {self.amount :,}{currency_emoji}"
            case 0:
                return f"Loss -{self.amount :,}{currency_emoji}"

    def is_exceeds_your(self) -> int:
        return self.your_value > 21

    def is_exceeds_dealer(self) -> int:
        return self.dealer_value > 21

    def go_dealer(self) -> None:
        while True:
            win_cards = []
            for card in self.cards:
                res = self.calculate_result(self.dealer_cards + [card])
                if 21 >= res:
                    win_cards.append(card)
            _log.debug('Win cards: %s, Chance: %s', len(
                win_cards), len(win_cards) / len(self.cards))
            if len(win_cards) / len(self.cards) >= 0.4:
                self.add_dealer_card()
            else:
                break

    def add_dealer_card(self) -> None:
        self.dealer_cards.append(self.get_random_cart())

    def add_your_card(self) -> None:
        self.your_cards.append(self.get_random_cart())

    def complete(self) -> None:
        _blackjack_games.pop(f'{self.member.guild.id}:{self.member.id}', None)

    @staticmethod
    def calculate_result(_cards: List[str]) -> int:
        result = 0
        count_of_none = 0
        for val in map(BlackjackGame.cards.__getitem__, _cards):
            if val is None:
                count_of_none += 1
            else:
                result += val
        for _ in range(count_of_none):
            if result+11 > 21:
                result += 1
            else:
                result += 11
        return result

    def get_random_cart(self) -> str:
        val = random.choice(list(self.cards))
        self.cards.pop(val)
        return val


class LordTemplate:
    def findall(self, string: str) -> List[Tuple[str, str]]:
        return REGEXP_FORMAT.findall(string)

    def parse_key(self, var: str) -> Tuple[str, Optional[str]]:
        if '|' not in var:
            return var.strip(), None

        key, *defaults = var.split('|')
        return key.strip(), '|'.join(defaults).strip()

    def parse_value(self, variables: List[Tuple[str, str]], forms: dict) -> dict:
        data = {}
        for every, var in variables:
            key, default = self.parse_key(var)
            if key in forms:
                data[every] = forms[key]
                if not data[every] and default is not None:
                    data[every] = default
            elif '.' in key and key.split('.')[1] and key.split('.')[0] in forms:
                value = forms[key.split('.')[0]]

                for v in key.split('.')[1:]:
                    if value is None:
                        break
                    value = getattr(value, v, None)

                data[every] = value
                if not value and default is not None:
                    data[every] = default
            elif default is not None:
                data[every] = default
        return data

# TODO: Fix formating


def lord_format(string: Any, forms: dict) -> str:
    if not isinstance(string, str):
        string = orjson.dumps(string).decode()

    template = LordTemplate()
    variables = template.findall(string)
    values = template.parse_value(variables, forms)
    for old, new in values.items():
        string = string.replace(old, str(new))
    return string


class TranslatorFlags:
    def __init__(self, longopts: list[str] = []):
        self.longopts = longopts

    async def convert(self, ctx: commands.Context, text: str) -> Any:
        args = text.split()
        self.flags = dict(map(lambda item: (item[0].removeprefix(
            '--'), item[1]), getopt.getopt(args, '', self.longopts)[0]))
        return self

    def get(self, key: str):
        if key in self.flags and self.flags[key] == '':
            return True
        return self.flags.get(key)

    def __class_getitem__(cls, *args: str):
        return cls(args)


async def get_emoji(guild_id: int, name: str):
    gdb = GuildDateBases(guild_id)
    system_emoji = await gdb.get('system_emoji')
    return ether.every_emojis[name][system_emoji]


def get_emoji_as_color(system_emoji: int, name: str):
    return ether.every_emojis[name][system_emoji]


@lru_cache()
def get_parser_args():
    parser = argparse.ArgumentParser(description='Starting a bot with arguments.', exit_on_error=False)
    parser.add_argument('--token')
    parser.add_argument('--log_level', choices=['DEBUG', 'INFO', 'ERROR'])
    parser.add_argument('--dev', action='store_true')
    parser.add_argument('--api', action='store_true')

    args = parser.parse_args()
    return {k: v for k, v in args._get_kwargs()
            if v is not None}


@overload
async def get_emoji_wrap(gdb: GuildDateBases) -> Callable[[str], str]: ...


@overload
async def get_emoji_wrap(guild_id: int) -> Callable[[str], str]: ...


async def get_emoji_wrap(guild_data: GuildDateBases | int) -> Callable[[str], str]:
    if isinstance(guild_data, GuildDateBases):
        gdb = guild_data
    else:
        gdb = GuildDateBases(guild_data)
    system_emoji = await gdb.get('system_emoji')

    def _get_emoji_inner(name: str):
        return ether.every_emojis[name][system_emoji]
    return _get_emoji_inner


async def clone_message(message: nextcord.Message) -> dict:
    content = message.content
    embeds = message.embeds
    files = await asyncio.gather(*[attach.to_file(spoiler=attach.is_spoiler())
                                   for attach in message.attachments])

    return {
        "content": content,
        "embeds": embeds,
        "files": files
    }


class LordTimerHandler:
    def __init__(self, loop: asyncio.AbstractEventLoop) -> None:
        self.loop = loop
        self.data: Dict[Union[str, int], TimerHandle] = {}

    def create_timer_handler(
        self,
        delay: float,
        coro: Coroutine,
        key: Optional[Union[str, int]] = None
    ):
        th = self.loop.call_later(delay,  self.loop.create_task, coro)
        if key is not None:
            _log.trace(f"Create new timer handle {coro.__name__} (ID:{key})")
            self.data[key] = th

    def close_as_key(self, key: Union[str, int]):
        th = self.data.get(key)
        if th is None:
            return
        arg = th._args[0]
        if asyncio.iscoroutine(arg):
            arg.close()
        th.cancel()

    def close_as_th(self, th: TimerHandle):
        arg = th._args and th._args[0]
        if asyncio.iscoroutine(arg):
            arg.close()
        th.cancel()


def parse_fission(iterable: Iterable[T], count: int) -> list[list[T]]:
    ret = []
    for index, value in enumerate(iterable):
        ret_index = int(index // count)
        try:
            values = ret[ret_index]
        except IndexError:
            values = []
            ret.append(values)
        values.append(value)
    return ret


class AsyncSterilization(Generic[T]):
    if TYPE_CHECKING:
        cls: type[T]

        def __new__(_cls, cls: type[T], *args, **kwargs) -> AsyncSterilization[T]:
            ...

    def __init__(self, cls) -> None:
        self.cls = cls

    def __repr__(self) -> str:
        return f"<{type(self).__name__} {self.cls!r}>"

    async def __call__(self, *args: Any, **kwds: Any) -> T:
        self = self.cls.__new__(self.cls)
        await self.__init__(*args, **kwds)
        return self


@AsyncSterilization
class GuildEmoji:
    async def __init__(self, guild_data: GuildDateBases | int) -> None:
        if isinstance(guild_data, GuildDateBases):
            gdb = guild_data
        else:
            gdb = GuildDateBases(guild_data)
        self.system_emoji = await gdb.get('system_emoji')
        self.data = {}

        for name, data in ether.every_emojis.items():
            self.data[name] = data[self.system_emoji]
            setattr(self, name, data[self.system_emoji])

    def get(self, name: str) -> str:
        return self.data[name]


def to_rgb(color: str | int):
    if isinstance(color, str):
        color = hex_int(color.strip(' #0x')[:6])

    def _get_byte(byte: int) -> int:
        return (color >> (8 * byte)) & 0xFF
    rgb = _get_byte(2), _get_byte(1), _get_byte(0)
    return rgb


def get_distance(color1_lab, color2):
    color2_rgb = sRGBColor(*to_rgb(color2))
    color2_lab = convert_color(color2_rgb, LabColor)
    dist = delta_e_cie2000(color1_lab, color2_lab)
    return dist


@lru_cache()
def find_color_emoji(color):
    if not isinstance(color, tuple):
        color = to_rgb(color)
    color1_rgb = sRGBColor(*color)
    color1_lab = convert_color(color1_rgb, LabColor)

    res = []
    for clr in colors:
        dist = get_distance(color1_lab, clr)
        res.append(dist)

    min_dist = min(res)
    hex_color = list(colors.keys())[res.index(min_dist)]
    return colors[hex_color]


@dataclass
class ItemLordTimeHandler:
    delay: Union[int, float]
    coro: Coroutine
    key: Union[str, int]
    th: TimerHandle = field(init=False)


class LordTimeHandler:
    __instance = None

    def __new__(cls, loop: Optional[asyncio.AbstractEventLoop] = None) -> None:
        if cls.__instance is None:
            cls.__instance = object.__new__(cls)
        return cls.__instance

    def __init__(self, loop: Optional[asyncio.AbstractEventLoop] = None) -> None:
        self.loop = loop
        self.data: Dict[Union[str, int], ItemLordTimeHandler] = {}

    def create(
        self,
        delay: float,
        coro: Coroutine,
        key: Union[str, int]
    ) -> ItemLordTimeHandler:
        _log.trace('Create new temp task %s (%s)', coro.__name__, key)
        ilth = ItemLordTimeHandler(delay, coro, key)
        th = self.loop.call_later(delay, self.complete, ilth)
        ilth.th = th
        self.data[key] = ilth
        return ItemLordTimeHandler

    def complete(self, ilth: ItemLordTimeHandler) -> None:
        _log.trace('Complete temp task %s (%s)', ilth.coro.__name__, ilth.key)
        self.loop.create_task(ilth.coro, name=ilth.key)
        self.data.pop(ilth.key, None)

    def close(self, key: Union[str, int]) -> ItemLordTimeHandler:
        ilth = self.data.pop(key, None)

        if ilth is None:
            return

        ilth.coro.close()
        ilth.th.cancel()
        return ilth

    def call(self, key: Union[str, int]) -> None:
        ilth = self.get(key)

        if ilth is None:
            return

        ilth.th._run()
        self.close(key)

    def increment(self, delay: Union[float, int], key: Union[str, int]) -> None:
        ilth = self.close(key)

        ilth.delay = delay
        th = self.loop.call_later(delay, self.complete, ilth)
        ilth.th = th
        self.data[key] = ilth

    def get(self, key: Union[str, int]) -> Optional[ItemLordTimeHandler]:
        return self.data.get(key)


def clamp(val: Union[int, float],
          minv: Union[int, float],
          maxv: Union[int, float]) -> Union[int, float]:
    return min(maxv, max(minv, val))


def is_default_emoji(text: str) -> bool:
    text = text.strip()
    return text in emoji.EMOJI_DATA


def is_custom_emoji(text: str) -> bool:
    text = text.strip()
    if regex.fullmatch(r'<a?:.+?:\d{18,}>', text):
        return True
    return False


def is_emoji(text: str) -> bool:
    return is_default_emoji(text) or is_custom_emoji(text)


def randquan(quan: int) -> int:
    if 0 >= quan:
        raise ValueError
    return random.randint(10**(quan-1), int('9'*quan))


def generate_random_token() -> Tuple[str, str]:
    message = randquan(100).to_bytes(100)
    key = Fernet.generate_key()
    token = Tokenizer.encrypt(message, key)
    return key.decode(), token.decode()


def decrypt_token(key: str, token: str) -> int:
    res = Tokenizer.decrypt(token.encode(), key.encode())
    return int.from_bytes(res)


async def get_random_quote(lang: str = 'en'):
    url = f"https://api.forismatic.com/api/1.0/?method=getQuote&format=json&lang={lang}"
    async with aiohttp.ClientSession() as session:
        async with session.post(url) as responce:
            json = await responce.json()
            return json


class TimeCalculator:
    def __init__(
        self,
        default_coefficient: int = 60,
        refundable: T = int,
        coefficients: Optional[dict] = None,
        operatable_time: bool = False,
        errorable: bool = True
    ) -> None:
        self.default_coefficient = default_coefficient
        self.refundable = refundable
        self.operatable_time = operatable_time
        self.errorable = errorable

        if coefficients is None:
            self.coefficients = {
                's': 1,
                'm': 60,
                'h': 3600,
                'd': 86400
            }
        else:
            self.coefficients = coefficients

    def __class_getitem__(cls, value: Any) -> Self:
        return cls(operatable_time=value)

    @overload
    def convert(
        self,
        argument: str
    ) -> T:
        pass

    @overload
    def convert(
        self,
        ctx: commands.Context,
        argument: str
    ) -> Coroutine[Any, Any, T]:
        pass

    def convert(self, *args) -> T | Coroutine[Any, Any, T]:
        if not isinstance(self, TimeCalculator):
            args = (self,)+args
            self = TimeCalculator()

        try:
            return self.async_convert(*args)
        except Exception:
            pass

        try:
            return self.basic_convert(*args)
        except Exception:
            pass

        if self.errorable:
            raise TypeError
        return None

    def basic_convert(
        self,
        argument: Any
    ) -> T:
        try:
            return int(argument)
        except ValueError:
            pass

        if not (isinstance(argument, str)
                and regex.fullmatch(r'\s*(\d+[a-zA-Z\s]+){1,}', argument)):
            raise TypeError('Format time is not valid!')

        timedate: list[tuple[str, str]] = regex.findall(
            r'(\d+)([a-zA-Z\s]+)', argument)
        ftime = 0

        for number, word in timedate:
            if word.strip() not in self.coefficients:
                raise TypeError('Format time is not valid!')

            multiplier = self.coefficients[word.strip()]
            ftime += int(number)*multiplier

        if not ftime:
            raise TypeError('Format time is not valid!')
        if self.operatable_time:
            ftime += time.time()

        return self.refundable(ftime)

    async def async_convert(
        self,
        ctx: commands.Context,
        argument: Any
    ) -> T:
        return self.basic_convert(argument)


def translate_to_timestamp(arg: str) -> int | None:
    tdts = ['%H:%M', '%H:%M:%S', '%d.%m.%Y', '%d.%m.%Y %H:%M', '%d.%m.%Y %H:%M:%S', '%H:%M %d.%m.%Y',
            '%H:%M:%S %d.%m.%Y', '%Y-%m-%d', '%H:%M %Y-%m-%d', '%H:%M:%S %Y-%m-%d',
            '%Y-%m-%d %H:%M', '%Y-%m-%d %H:%M:%S']
    for th in tdts:
        with contextlib.suppress(ValueError):
            tdt = datetime.strptime(arg, th)
            if tdt.year == 1900 and tdt.month == 1 and tdt.day == 1:
                today = datetime.today()
                tdt = datetime(
                    today.year,
                    today.month,
                    today.day,
                    tdt.hour,
                    tdt.minute,
                    tdt.second
                )
            return tdt.timestamp()

    with contextlib.suppress(ValueError):
        return TimeCalculator(operatable_time=True).convert(arg)

    return None


@lru_cache()
def get_award(number):
    awards = {
        1: '🥇',
        2: '🥈',
        3: '🥉'
    }
    award = awards.get(number, number)
    return award


def randfloat(a: float | int, b: float | int, scope: int = 14) -> float:
    return random.randint(int(a*10**scope), int(b*10**scope)) / 10**scope


class GeneratorMessageDictPop(dict):
    def __init__(self, data):
        self.data = data
        super().__init__(data)

    if not TYPE_CHECKING:
        def get(self, key, default=None):
            return self.data.pop(key, default)

        def __getitem__(self, key: Any) -> Any:
            return self.data.pop(key)


class GeneratorMessage:
    def __init__(self, data: Union[str, dict]) -> None:
        self.data = data

    @staticmethod
    def check_empty(data: dict) -> bool:
        plain_text = data.get('plainText')
        content = data.get('content')
        embed = data.get('embed')
        embeds = data.get('embeds')
        return not any((
            content,
            plain_text,
            embed,
            embeds
        ))

    def decode_data(self):
        if not isinstance(self.data, dict):
            try:
                decode_data = orjson.loads(self.data)
            except orjson.JSONDecodeError:
                decode_data = self.data
        else:
            decode_data = self.data.copy()
        if not isinstance(decode_data, dict):
            decode_data = str(decode_data)
        return decode_data

    def get_error(self, error_status: Optional[int] = None):

        if error_status == 5415:
            content = (
                f'{Emoji.cross} **Content** and **plain text** cannot be combined.\n'
                'If you see this message somewhere in the components, contact the server administrators.'
            )
        elif error_status == 5410:
            content = (
                f'{Emoji.cross} **Embed** and **embeds** cannot be combined.\n'
                'If you see this message somewhere in the components, contact the server administrators.'
            )
        elif error_status == 404:
            content = (
                f'{Emoji.cross} The message is empty.\n'
                'If you see this message somewhere in the components, contact the server administrators.'
            )
        else:
            content = f'{Emoji.cross} If you see this message somewhere in the components, contact the server administrators.'
        return {
            "content": content
        }

    @lru_cache()
    def parse(self, with_empty: bool = False):
        data = self.decode_data()
        ret = {}

        if isinstance(data, str):
            data = {'content': data}

        data.pop('attachments', MISSING)
        plain_text = data.pop('plainText', MISSING)
        content = data.pop('content', MISSING)
        embed = self.parse_embed(data)
        embeds = self.parse_embeds(data.pop('embeds', MISSING))
        flags = data.pop('flags', MISSING)

        if content is not MISSING and plain_text is not MISSING:
            return self.get_error(5415)
        if embed is not MISSING and embeds is not MISSING:
            return self.get_error(5410)

        if content is not MISSING:
            ret['content'] = content
        elif plain_text is not MISSING:
            ret['content'] = plain_text
        else:
            ret['content'] = None

        if embed is not MISSING:
            ret['embeds'] = [embed]
        elif embeds is not MISSING:
            ret['embeds'] = embeds
        else:
            ret['embeds'] = []

        if flags is not MISSING:
            ret['flags'] = nextcord.MessageFlags._from_value(flags)

        if data:
            _log.trace('Message data: %s', ret)
            _log.trace('Exclude data: %s', data)

        if with_empty and self.check_empty(ret):
            return self.get_error(404)

        return ret

    def parse_embed(self, data: dict):
        new_data = GeneratorMessageDictPop(data)

        with contextlib.suppress(KeyError):
            timestamp = data["timestamp"]
            if isinstance(timestamp, (int, float)):
                try:
                    data["timestamp"] = datetime.fromtimestamp(
                        float(timestamp)).isoformat()
                except OSError:
                    data["timestamp"] = datetime.fromtimestamp(
                        float(timestamp)//1000).isoformat()

        with contextlib.suppress(KeyError, ValueError):
            color = data.pop("color")
            if isinstance(color, str):
                if color.startswith(('0x', '#')):
                    color = int(color.removeprefix('#').removeprefix('0x'), 16)
            data["color"] = int(color)

        for arg in ('thumbnail', 'image'):
            with contextlib.suppress(KeyError):
                url = data[arg]
                if (
                    not url
                    or (isinstance(url, str) and url.lower() == 'none')
                    or (isinstance(url, dict) and url.get('url').lower() == 'none')
                ):
                    del data[arg]
                    continue
                if isinstance(url, str):
                    data[arg] = {
                        'url': url
                    }

        embed = nextcord.Embed.from_dict(new_data)

        if data:
            _log.trace('Exclude embed data: %s', new_data.data)

        if embed:
            return embed
        else:
            return MISSING

    def parse_embeds(self, data):
        if data is MISSING:
            return MISSING

        if data is None or not isinstance(data, list):
            return []

        embeds = []
        for item in data:
            embed = self.parse_embed(item)
            if embed is not MISSING:
                embeds.append(embed)

        return embeds


def generate_message(content: str, *, with_empty: bool = False) -> dict:
    message = GeneratorMessage(content)
    return message.parse(with_empty)


async def generator_captcha(num):
    text = "".join([random.choice(string.ascii_uppercase) for _ in range(num)])
    captcha_image = ImageCaptcha(
        width=400,
        height=220,
        fonts=["assets/Nunito-Black.ttf"],
        font_sizes=(40, 70, 100)
    )
    data: BytesIO = captcha_image.generate(text)
    return data, text


def cut_back(string: str, length: int):
    ellipsis = "..."
    current_lenght = len(string)
    if length >= current_lenght:
        return string

    cropped_string = string[:length-len(ellipsis)].strip()
    new_string = f"{cropped_string}{ellipsis}"
    return new_string


def draw_gradient(
    img: Image.Image,
    start: Tuple[int, int, int],
    end: Tuple[int, int, int]
):
    px = img.load()
    for y in range(0, img.height):
        color = tuple(int(start[i] + (end[i] - start[i])
                      * y / img.height) for i in range(3))
        for x in range(0, img.width):
            px[x, y] = color


def add_gradient(
    backgroud: Image.Image,
    font: ImageFont.FreeTypeFont,
    text: str,
    height: int,
    color_start: Tuple[int, int, int],
    color_stop: Tuple[int, int, int]
) -> None:
    w, h = font.getbbox(text)[2:]

    gradient = Image.new("RGB", (w, h))
    draw_gradient(gradient, color_start, color_stop)

    im_text = Image.new("RGBA", (w, h))
    d = ImageDraw.Draw(im_text)
    d.text((0, 0), text, font=font)

    backgroud.draft("RGBA", backgroud.size)
    backgroud.paste(
        gradient,
        (int(backgroud.size[0]/2-im_text.size[0]/2), height),
        im_text
    )


async def generate_welcome_image(member: nextcord.Member, background_link: str) -> bytes:
    bot: LordBot = member._state._get_client()
    session = bot.session

    background_image = await load_image_async(background_link, session=session)
    background = Editor(background_image).resize((800, 450))

    profile_image = await load_image_async(
        member.display_avatar.with_size(128).url, session=session)
    profile = Editor(profile_image).resize((150, 150)).circle_image()

    nunito = Font("assets/Nunito-ExtraBold.ttf", 40)
    nunito_small = Font("assets/Nunito-Black.ttf", 25)
    nunito_light = Font("assets/Nunito-Black.ttf", 20)

    background.paste(profile, (325, 90))
    background.ellipse((325, 90), 150, 150, outline=(
        125, 249, 255), stroke_width=4)
    add_gradient(
        background.image,
        nunito.font,
        f"WELCOME TO {member.guild.name.upper()}",
        260,
        (253, 187, 45),
        (34, 193, 195)
    )
    background.text(
        (400, 320),
        member.display_name,
        color="#ff00a6",
        font=nunito_small,
        align="center"
    )
    background.text(
        (400, 360),
        f"You are the {member.guild.member_count}th Member",
        color="#F5923B",
        font=nunito_light,
        align="center",
    )

    return background.image_bytes


def replace_dict_key(data: dict, old, new) -> dict:
    data_keys = list(data.keys())
    index = data_keys.index(old)
    data_keys[index] = new

    new_data = dict.fromkeys(data_keys)

    for key in data_keys:
        if key == new:
            new_data[key] = data[old]
        else:
            new_data[key] = data[key]

    return new_data
