import re
from typing import Callable

from functools import lru_cache

from bot.databases import GuildDateBases
from bot.resources import ether

from colormath.color_objects import sRGBColor
from colormath.color_conversions import convert_color
from .misc import to_rgb, get_distance

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


def is_default_emoji(text: str) -> bool:
    import emoji
    return text.strip() in emoji.EMOJI_DATA


def is_custom_emoji(text: str) -> bool:
    return bool(re.fullmatch(r'<a?:.+?:\d{18,}>', text.strip()))


def is_emoji(text: str) -> bool:
    return is_default_emoji(text) or is_custom_emoji(text)


async def get_emoji(guild_id: int, name: str):
    gdb = GuildDateBases(guild_id)
    system_emoji = await gdb.get('system_emoji')
    return ether.every_emojis[name][system_emoji]


def get_emoji_as_color(system_emoji: int, name: str):
    return ether.every_emojis[name][system_emoji]


@lru_cache()
def find_color_emoji(color):

    if not isinstance(color, tuple):
        color = to_rgb(color)
    color1_rgb = to_rgb(color)

    color1_lab = convert_color(sRGBColor(*color1_rgb), target_cs='lab')

    res = []
    for clr in colors:
        dist = get_distance(color1_lab, clr)
        res.append(dist)

    min_dist = min(res)
    hex_color = list(colors.keys())[res.index(min_dist)]
    return colors[hex_color]


async def get_emoji_wrap(guild_data: GuildDateBases | int) -> Callable[[str], str]:
    if isinstance(guild_data, GuildDateBases):
        gdb = guild_data
    else:
        gdb = GuildDateBases(guild_data)
    system_emoji = await gdb.get('system_emoji')

    def _get_emoji_inner(name: str):
        return ether.every_emojis[name][system_emoji]

    return _get_emoji_inner


@lru_cache()
class GuildEmoji:
    def __init__(self, guild_data: GuildDateBases | int) -> None:
        if isinstance(guild_data, GuildDateBases):
            gdb = guild_data
        else:
            gdb = GuildDateBases(guild_data)
        self.system_emoji = gdb.get_cache('system_emoji')
        self.data = {}

        for name, data in ether.every_emojis.items():
            self.data[name] = data[self.system_emoji]
            setattr(self, name, data[self.system_emoji])

    def get(self, name: str) -> str:
        return self.data[name]
