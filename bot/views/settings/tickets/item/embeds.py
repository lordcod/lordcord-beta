
from typing import Any,  Optional, Tuple
import nextcord

from bot.databases.handlers.guildHD import GuildDateBases
from bot.databases.varstructs import TicketsPayload
from bot.languages import i18n
from bot.misc.utils import get_emoji_as_color
from bot.resources.info import DEFAULT_TICKET_TYPE


def get_emoji(system_emoji: str, value: Any) -> str:
    if value:
        return get_emoji_as_color(system_emoji, 'ticon')
    else:
        return get_emoji_as_color(system_emoji, 'ticoff')


def join_args(*args: Tuple[str, Optional[Any]]) -> str:
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


async def get_embed(guild: nextcord.Guild, message_id: int) -> nextcord.Embed:
    gdb = GuildDateBases(guild.id)
    color = await gdb.get('color')
    locale = await gdb.get('language')
    system_emoji = await gdb.get('system_emoji')
    emoji_ticoff = get_emoji_as_color(system_emoji, 'ticoff')
    emoji_ticon = get_emoji_as_color(system_emoji, 'ticon')
    tickets: TicketsPayload = await gdb.get('tickets')
    ticket_data = tickets[message_id]
    ticket_index = list(tickets.keys()).index(message_id)+1
    emoji = nextcord.PartialEmoji.from_str(get_emoji_as_color(system_emoji, f'circle{ticket_index}'))

    enabled = ticket_data.get('enabled')
    ticket_type = ticket_data.get('type', DEFAULT_TICKET_TYPE)
    channel_id = ticket_data.get('channel_id')
    message_id = ticket_data.get('message_id')
    mod_roles = ticket_data.get('moderation_roles', [])
    approved_roles = ticket_data.get('approved_roles')
    global_tickets_limit = ticket_data.get('global_user_tickets_limit')
    tickets_limit = ticket_data.get('user_tickets_limit')
    categories = ticket_data.get('categories')
    user_closed = ticket_data.get('user_closed', True)
    modals = ticket_data.get('modals')
    faq = ticket_data.get('faq', {})
    faq_items = faq.get('items')

    channel = guild.get_channel(channel_id)
    message = channel.get_partial_message(message_id)

    ticket_type_message = (
        i18n.t(locale, 'settings.tickets.embeds.msg_type.channels')
        if ticket_type == 1
        else i18n.t(
            locale, 'settings.tickets.embeds.msg_type.threads')
    )

    if faq and faq_items:
        faq_message = i18n.t(locale, 'settings.tickets.embeds.faq.info',
                             count=len(faq_items),
                             emoji_ticoff=emoji_ticoff,
                             emoji_ticon=emoji_ticon)
    else:
        faq_message = i18n.t(locale, 'settings.tickets.embeds.faq.woc',
                             emoji_ticoff=emoji_ticoff,
                             emoji_ticon=emoji_ticon)

    if categories:
        cat_message = i18n.t(locale, 'settings.tickets.embeds.category.info',
                             count=len(categories),
                             emoji_ticoff=emoji_ticoff,
                             emoji_ticon=emoji_ticon)
    else:
        cat_message = i18n.t(locale, 'settings.tickets.embeds.category.woc',
                             emoji_ticoff=emoji_ticoff,
                             emoji_ticon=emoji_ticon)

    if modals:
        modal_message = i18n.t(locale, 'settings.tickets.embeds.modals.info',
                               count=len(modals),
                               emoji_ticoff=emoji_ticoff,
                               emoji_ticon=emoji_ticon)
    else:
        modal_message = i18n.t(locale, 'settings.tickets.embeds.modals.woc',
                               emoji_ticoff=emoji_ticoff,
                               emoji_ticon=emoji_ticon)

    description_info = i18n.t(locale, 'settings.tickets.embeds.description_info',
                              channel=channel.mention,
                              message=message.jump_url
                              )

    if ticket_type == 1:
        category = guild.get_channel(ticket_data.get('category_id'))
        closed_category = guild.get_channel(
            ticket_data.get('closed_category_id'))
        if category is not None:
            description_info += '\n'+i18n.t(locale,
                                            'settings.tickets.embeds.category',
                                            category=category.mention)
        if closed_category is not None:
            description_info += '\n'+i18n.t(locale,
                                            'settings.tickets.embeds.closed_category',
                                            category=closed_category.mention)

    embed = nextcord.Embed(
        color=color,
        description=i18n.t(locale, 'settings.tickets.embeds.description',
                           info=description_info),
    )
    embed.set_author(
        name=i18n.t(locale, 'settings.tickets.init.ticket',
                    index=ticket_index),
        icon_url=emoji.url
    )

    embed.add_field(
        name='',
        value=join_args(
            (i18n.t(locale, 'settings.tickets.embeds.enabled'), get_emoji(system_emoji, enabled)),
            (i18n.t(locale, 'settings.tickets.embeds.user_closed'),
             get_emoji(system_emoji, user_closed)),
            (i18n.t(locale, 'settings.tickets.embeds.allowed_roles.desc')+(', '.join([
                role.mention
                for role_id in approved_roles or []
                if (role := guild.get_role(role_id))
            ]) or i18n.t(locale, 'settings.tickets.embeds.allowed_roles.nf')),
                approved_roles is not None),
            (i18n.t(locale, 'settings.tickets.embeds.agent_roles'), ', '.join([
                role.mention
                for role_id in mod_roles
                if (role := guild.get_role(role_id))
            ])),
            (i18n.t(locale, 'settings.tickets.embeds.ticket_type'), ticket_type_message),
            (i18n.t(locale, 'settings.tickets.embeds.global_limit'), global_tickets_limit),
            (i18n.t(locale, 'settings.tickets.embeds.category_limit'), tickets_limit),
            (faq_message, ),
            (cat_message, ),
            (modal_message, ),
        )
    )

    return embed
