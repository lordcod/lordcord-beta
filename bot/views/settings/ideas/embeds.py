from typing import Any, Tuple
import nextcord

from bot.databases.handlers.guildHD import GuildDateBases
from bot.databases.varstructs import IdeasPayload
from bot.languages import i18n
from bot.misc.time_transformer import display_time
from bot.misc.utils import get_emoji_as_color
from bot.resources.info import DEFAULT_IDEAS_ALLOW_IMAGE


def get_emoji(system_emoji: str, value: Any) -> str:
    if value:
        return get_emoji_as_color(system_emoji, 'ticon')
    else:
        return get_emoji_as_color(system_emoji, 'ticoff')


def join_args(*args: Tuple[str, Any] | Tuple[str]) -> str:
    res = []
    for data in args:
        if len(data) == 1:
            res.append(data[0])
            continue

        text, value = data
        if not value:
            continue

        res.append(f'{text}{value}')
    return '\n'.join(res)


async def get_embed(guild: nextcord.Guild) -> nextcord.Embed:
    gdb = GuildDateBases(guild.id)
    color: int = await gdb.get('color')
    system_emoji = await gdb.get('system_emoji')
    locale: str = await gdb.get('language')
    ideas: IdeasPayload = await gdb.get('ideas', {})
    channel_suggest = guild.get_channel(ideas.get("channel_suggest_id"))
    channel_offers = guild.get_channel(ideas.get("channel_offers_id"))
    channel_approved = guild.get_channel(
        ideas.get("channel_approved_id"))
    enabled = ideas.get('enabled')
    cooldown = ideas.get('cooldown', 0)
    revoting = ideas.get('revoting')
    allow_image = ideas.get('allow_image', DEFAULT_IDEAS_ALLOW_IMAGE)
    thread_open = ideas.get('thread_open')
    thread_delete = ideas.get('thread_delete')
    moderation_role_ids = ideas.get("moderation_role_ids", [])
    moderation_roles = filter(lambda item: item is not None,
                              map(guild.get_role,
                                  moderation_role_ids))

    embed = nextcord.Embed(
        title=i18n.t(locale, 'settings.ideas.init.title'),
        description=i18n.t(locale, 'settings.ideas.init.description'),
        color=color
    )

    description = join_args(
        (i18n.t(locale, 'settings.ideas.value.suggest'),
         channel_suggest and channel_suggest.mention),
        (i18n.t(locale, 'settings.ideas.value.offers'),
         channel_offers and channel_offers.mention),
        (i18n.t(locale, 'settings.ideas.value.approved'),
         channel_approved and channel_approved.mention),
        ('',),
        (i18n.t(locale, 'settings.ideas.value.enabled'),
         get_emoji(system_emoji, enabled)),
        (i18n.t(locale, 'settings.ideas.value.cooldown'),
         display_time(cooldown, locale, max_items=2)),
        (i18n.t(locale, 'settings.ideas.value.mod_roles'),
         '・'.join([role.mention for role in moderation_roles])),
        (i18n.t(locale, 'settings.ideas.value.revoting'),
         get_emoji(system_emoji, revoting)),
        (i18n.t(locale, 'settings.ideas.value.allow_image'),
         get_emoji(system_emoji, allow_image)),
        (i18n.t(locale, 'settings.ideas.value.thread_delete'),
         get_emoji(system_emoji, thread_delete)),
        (i18n.t(locale, 'settings.ideas.value.thread_open'),
         get_emoji(system_emoji, thread_open)),
    )

    if description:
        embed.description += '\n\n'+description

    return embed
