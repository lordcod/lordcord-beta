import nextcord
import orjson
from bot.databases.varstructs import IdeasComponentsPayload, IdeasMessagesPayload, IdeasPayload, IdeasReactionsPayload, TicketsItemPayload
from bot.resources.ether import ColorType, Emoji

DISCORD_SUPPORT_SERVER = 'https://discord.com/invite/np6RhahkZH'
SITE = 'https://lordcord.fun'

DEFAULT_MAPPING_LANGUAGE = {'en': 'en-US', 'es': 'es-ES'}

DEFAULT_BOT_COLOR = int(ColorType.sliv)

DEFAULT_PREFIX = 'l.'
DEFAULT_COLOR = 2829617
DEFAULT_LANGUAGE = 'en'
DEFAULT_EMOJI = str(Emoji.diamod)
DEFAULT_ECONOMY_THEFT = {
    'cooldown': 86400,
    'jail': True,
    'time_prison': {
        'min': 86400,
        'max': 259200,
        'adaptive': 86400
    }
}
DEFAULT_ECONOMY_SETTINGS = {
    'emoji': DEFAULT_EMOJI,
    "daily": 10,
    "weekly": 50,
    "monthly": 200,
    'work': {
        'min': 5,
        'max': 30,
        'cooldown': 60 * 60 * 6
    },
    'bet': {
        'min': 10,
        'max': 1000
    },
    'theft': DEFAULT_ECONOMY_THEFT
}
DEFAULT_GUILD_DATA = {
    'language': 'en',
    'prefix': 'l.',
    'color': 1974050,
    'economic_settings': {},
    'greeting_message': {},
    'auto_roles': {},
    'ideas': {},
    'music_settings': {},
    'auto_translate': {},
    'command_permissions': {},
    'tickettool': {},
    'invites': {},
    'giveaways': {},
    'polls': {},
    'logs': {},
    'role_reactions': {},
    'delete_task': 0
}

COUNT_ROLES_PAGE = 5

DEFAULT_TICKET_PAYLOAD: TicketsItemPayload = {
    'names': {
        'open': '{ticket.count.total}-ticket',
        'close': None
        # Disabled until the problem is resolved
        # 'close': '{ticket.count.total}-closed'
    },
    'messages': {
        'panel': {
            "content": None,
            "title": "Tickets",
            "description": "If you have a question about the operation of the server, click on interaction to create a request.",
            "color": "{guild.color}",
            "footer": {
                "text": "{bot.displayName}",
                "timestamp": "{today_dt}",
                'icon_url': '{bot.avatar}'
            }, "thumbnail": ""
        },
        'controller': {
            "title": "Support team ticket controls",
            "color": "{guild.color}",
            "footer": {
                "timestamp": "{today_dt}"
            },
        },
        'close': {
            "title": "Action",
            "description": "The ticket is closed by {member.mention}",
            "color": 16765743,
            "footer": {
                "timestamp": "{today_dt}"
            },
        },
        'reopen': {
            "title": "Action",
            "description": "The ticket is opened by {member.mention}",
            "color": 53380,
            "footer": {
                "timestamp": "{today_dt}"
            },
        },
        'delete': {
            "title": "Action",
            "description": 'Ticket will be deleted in a few seconds',
            "color": 16718362,
            "footer": {
                "timestamp": "{today_dt}"
            },
        },
        'open': '{member} Welcome!',
        'category': None,
    },
    'buttons': {
        'category_placeholder': 'Select the category of the request',
        'modal_placeholder': 'Ticket Forms',
        'faq_placeholder': 'FAQ',
        'faq_option': {
            'label': 'Didn\'t find the answer?',
            'emoji': Emoji.tickets,
            'description': 'Click to create a request',
        },
        'faq_button_open': {
            'label': 'FAQ',
            'emoji': Emoji.faq,
            'style': nextcord.ButtonStyle.blurple,
        },
        'faq_button_create': {
            'label': 'Create appeal',
            'emoji': Emoji.tickets,
            'style': nextcord.ButtonStyle.secondary,
        },
        'close_button': {
            'label': "Close ticket",
            'emoji': "🔒",
            'style': nextcord.ButtonStyle.red,
        },
        'reopen_button': {
            'label': 'Reopen ticket',
            'emoji': '🔓',
            'style': nextcord.ButtonStyle.secondary,
        },
        'delete_button': {
            'label': 'Delete ticket',
            'emoji': '⛔',
            'style': nextcord.ButtonStyle.red,
        },
    }
}

DEFAULT_TICKET_PAYLOAD_RU: TicketsItemPayload = {
    'names': {
        'open': '{ticket.count.total}-ticket',
        'close': None,
        # Disabled until the problem is resolved
        # 'close': '{ticket.count.total}-closed'
    },
    'messages': {
        'panel': {
            "content": None,
            "title": "Тикет",
            "description": "Если у вас есть вопросы о работе сервера, нажмите на взаимодействие, чтобы создать запрос.",
            "color": "{guild.color}",
            "footer": {
                "text": "{bot.displayName}",
                "timestamp": "{today_dt}",
                'icon_url': '{bot.avatar}'
            },
            "thumbnail": ""
        },
        'open': '{member} Привет!',
        'category': None,
        'controller': {
            "title": "Контроль заявок в службе поддержки",
            "color": "{guild.color}",
            "footer": {
                "timestamp": "{today_dt}"
            },
        },
        'close': {
            "title": "Действие",
            "description": "Заявка закрыта {member.mention}",
            "color": 16765743,
            "footer": {
                "timestamp": "{today_dt}"
            },
        },
        'reopen': {
            "title": "Действие",
            "description": "Тикет открывается с помощью {member.mention}",
            "color": 53380,
            "footer": {
                "timestamp": "{today_dt}"
            },
        },
        'delete': {
            "title": "Действие",
            "description": 'Тикет будет удален через несколько секунд',
            "color": 16718362,
            "footer": {
                "timestamp": "{today_dt}"
            },
        },

    },
    'buttons': {
        'category_placeholder': 'Выберите категорию запроса',
        'modal_placeholder': 'Бланки тикета',
        'faq_placeholder': 'FAQ',
        'faq_option': {
            'label': 'Не нашли ответа на свой вопрос?',
            'emoji': Emoji.tickets,
            'description': 'Нажмите, чтобы создать запрос',
        },
        'faq_button_open': {
            'label': 'FAQ',
            'emoji': Emoji.faq,
            'style': nextcord.ButtonStyle.blurple,
        },
        'faq_button_create': {
            'label': 'Создать обращение',
            'emoji': Emoji.tickets,
            'style': nextcord.ButtonStyle.secondary,
        },
        'close_button': {
            'label': "Закрыть заявку",
            'emoji': "🔒",
            'style': nextcord.ButtonStyle.red,
        },
        'reopen_button': {
            'label': 'Повторно открыть билет',
            'emoji': '🔓',
            'style': nextcord.ButtonStyle.secondary,
        },
        'delete_button': {
            'label': 'Удалить заявку',
            'emoji': '⛔',
            'style': nextcord.ButtonStyle.red,
        },

    }
}

DEFAULT_TICKET_PERMISSIONS_OVER = {
    'moderator': nextcord.PermissionOverwrite(
        view_channel=True,
        send_messages=True,
        embed_links=True,
        attach_files=True,
        add_reactions=True,
        use_external_emojis=True,
        use_external_stickers=True,
        manage_messages=True,
        manage_threads=True,
        read_message_history=True
    ).pair(),
    'owner': nextcord.PermissionOverwrite(
        view_channel=True,
        send_messages=True,
        embed_links=True,
        attach_files=True,
        add_reactions=True,
        use_external_emojis=True,
        use_external_stickers=True,
        read_message_history=True
    ).pair(),
    'addtional': nextcord.PermissionOverwrite(
        view_channel=True,
        send_messages=True
    ).pair(),
    'everyone': nextcord.PermissionOverwrite(view_channel=False).pair()
}
DEFAULT_TICKET_PERMISSIONS = {k: (allow.value, deny.value)
                              for k, (allow, deny) in DEFAULT_TICKET_PERMISSIONS_OVER.items()}

DEFAULT_TWITCH_MESSAGE = '🎥 У __{stream.username}__ начался новый стрим!\nПрисоединяйтесь к нам сейчас: {stream.url}'
DEFAULT_YOUTUBE_MESSAGE = '🎥 Новое видео на YouTube от {video.username}!\nСмотрите прямо сейчас: {video.url}'

DEFAULT_TICKET_TYPE = 2
DEFAULT_TICKET_FAQ_TYPE = 2
DEFAULT_TICKET_LIMIT = 5

DEFAULT_IDEAS_MESSAGES: IdeasMessagesPayload = {
    'suggestion': {
        "title": 'Ideas',
        "description": (
            'Do you have a good idea?\n'
            'And you are sure that everyone will like it!\n'
            'Before you write it, make sure that there have been no such ideas yet!'
        ),
        "color": "{guild.color}"
    },
    'created': {
        "title": "AN OPEN IDEA",
        "description": ("An suggest from {member.mention}\n\n"
                        "{idea.content}"),
        "color": nextcord.Color.orange().value,
        "author": {
            "name": "{member.displayName}",
            "icon_url": "{member.avatar}"
        },
        "image": {
            "url": "{idea.image}"
        }
    },
    'accept': {
        "title": "APPROVED IDEA",
        "description": ("An suggest from {member.mention}\n\n"
                        "{idea.content}"),
        "color": nextcord.Color.green().value,
        "author": {
            "name": "{member.displayName}",
            "icon_url": "{member.avatar}"
        },
        "image": {
            "url": "{idea.image}"
        },
        "footer": {
            "text": "Approved | {idea.mod.displayName} | 👍 - {idea.promotedCount} | 👎 - {idea.demotedCount}",
            "icon_url": "{idea.mod.avatar}"
        }
    },
    'deny': {
        "title": "A REJECTED IDEA",
        "description": ("An suggest from {member.mention}\n\n"
                        "{idea.content}"),
        "color": nextcord.Color.red().value,
        "author": {
            "name": "{member.displayName}",
            "icon_url": "{member.avatar}"
        },
        "image": {
            "url": "{idea.image}"
        },
        "footer": {
            "text": "Refused |  {idea.mod.displayName} | 👍 - {idea.promotedCount} | 👎 - {idea.demotedCount}",
            "icon_url": "{idea.mod.avatar}"
        }
    },
}

_FIELDS_REASON = [
    {
        "name": 'Reason:',
        "value": "{idea.reason}",
        "inline": False
    }
]
DEFAULT_IDEAS_MESSAGES['accept_with_reason'] = DEFAULT_IDEAS_MESSAGES['accept'].copy()
DEFAULT_IDEAS_MESSAGES['accept_with_reason']["fields"] = _FIELDS_REASON

DEFAULT_IDEAS_MESSAGES['deny_with_reason'] = DEFAULT_IDEAS_MESSAGES['deny'].copy()
DEFAULT_IDEAS_MESSAGES['deny_with_reason']["fields"] = _FIELDS_REASON

DEFAULT_IDEAS_MESSAGES['approved'] = DEFAULT_IDEAS_MESSAGES['accept']
DEFAULT_IDEAS_MESSAGES['approved_with_reason'] = DEFAULT_IDEAS_MESSAGES['accept_with_reason']

DEFAULT_IDEAS_MESSAGES['reject'] = DEFAULT_IDEAS_MESSAGES['deny']
DEFAULT_IDEAS_MESSAGES['reject_with_reason'] = DEFAULT_IDEAS_MESSAGES['deny_with_reason']

DEFAULT_THREAD_NAME = 'Discussion of the idea from {member.username}'
DEFAULT_IDEAS_REVOTING = True
DEFAULT_IDEAS_ALLOW_IMAGE = True

DEFAULT_IDEAS_PAYLOAD: IdeasPayload = {
    'messages': DEFAULT_IDEAS_MESSAGES,
    'thread_name': DEFAULT_THREAD_NAME,
    'revoting': DEFAULT_IDEAS_REVOTING,
    'reactions': {
        'success': Emoji.tickmark,
        'crossed': Emoji.cross
    },
    'components': {
        'suggest': {
            'label': 'Suggest an idea',
            'style': nextcord.ButtonStyle.green
        },
        'approve': {
            'label': 'Approve',
            'style': nextcord.ButtonStyle.green
        },
        'deny': {
            'label': 'Deny',
            'style': nextcord.ButtonStyle.red
        },
        'like': {
            'emoji': '👍',
            'label': '{idea.promotedCount | 0}',
            'style': nextcord.ButtonStyle.gray
        },
        'dislike': {
            'emoji': '👎',
            'label': '{idea.demotedCount | 0}',
            'style': nextcord.ButtonStyle.gray
        },
    },
}


DEFAULT_IDEAS_MESSAGES_RU: IdeasMessagesPayload = {
    'suggestion': {
        "title": 'Идеи',
        "description": (
            'У вас есть хорошая идея?\n'
            'И вы уверены, что она всем понравится!\n'
            'Прежде чем писать, убедитесь, что таких идей еще не было!'
        ),
        "color": "{guild.color}"
    },
    'created': {
        "title": "ОТКРЫТАЯ ИДЕЯ",
        "description": ("Предложение от {member.mention}\n\n"
                        "{idea.content}"),
        "color": nextcord.Color.orange().value,
        "author": {
            "name": "{member.displayName}",
            "icon_url": "{member.avatar}"
        },
        "image": {
            "url": "{idea.image}"
        }
    },
    'accept': {
        "title": "ОДОБРЕННАЯ ИДЕЯ",
        "description": ("Предложение от {member.mention}\n\n"
                        "{idea.content}"),
        "color": nextcord.Color.green().value,
        "author": {
            "name": "{member.displayName}",
            "icon_url": "{member.avatar}"
        },
        "image": {
            "url": "{idea.image}"
        },
        "footer": {
            "text": "Одобренно | {idea.mod.displayName} | 👍 - {idea.promotedCount} | 👎 - {idea.demotedCount}",
            "icon_url": "{idea.mod.avatar}"
        }
    },
    'deny': {
        "title": "ОТВЕРГНУТАЯ ИДЕЯ",
        "description": ("Предложение от {member.mention}\n\n"
                        "{idea.content}"),
        "color": nextcord.Color.red().value,
        "author": {
            "name": "{member.displayName}",
            "icon_url": "{member.avatar}"
        },
        "image": {
            "url": "{idea.image}"
        },
        "footer": {
            "text": "Отказано |  {idea.mod.displayName} | 👍 - {idea.promotedCount} | 👎 - {idea.demotedCount}",
            "icon_url": "{idea.mod.avatar}"
        }
    },
}

_FIELDS_REASON_RU = [
    {
        "name": 'Причина:',
        "value": "{idea.reason}",
        "inline": False
    }
]
DEFAULT_IDEAS_MESSAGES_RU['accept_with_reason'] = DEFAULT_IDEAS_MESSAGES_RU['accept'].copy()
DEFAULT_IDEAS_MESSAGES_RU['accept_with_reason']["fields"] = _FIELDS_REASON_RU

DEFAULT_IDEAS_MESSAGES_RU['deny_with_reason'] = DEFAULT_IDEAS_MESSAGES_RU['deny'].copy(
)
DEFAULT_IDEAS_MESSAGES_RU['deny_with_reason']["fields"] = _FIELDS_REASON_RU

DEFAULT_IDEAS_MESSAGES_RU['approved'] = DEFAULT_IDEAS_MESSAGES_RU['accept']
DEFAULT_IDEAS_MESSAGES_RU['approved_with_reason'] = DEFAULT_IDEAS_MESSAGES['accept_with_reason']

DEFAULT_IDEAS_MESSAGES_RU['reject'] = DEFAULT_IDEAS_MESSAGES_RU['deny']
DEFAULT_IDEAS_MESSAGES_RU['reject_with_reason'] = DEFAULT_IDEAS_MESSAGES['deny_with_reason']

DEFAULT_THREAD_NAME_RU = 'Обсуждение идеи от {member.username}'

DEFAULT_IDEAS_PAYLOAD_RU: IdeasPayload = {
    'messages': DEFAULT_IDEAS_MESSAGES_RU,
    'thread_name': DEFAULT_THREAD_NAME_RU,
    'revoting': DEFAULT_IDEAS_REVOTING,
    'reactions': {
        'success': Emoji.tickmark,
        'crossed': Emoji.cross
    },
    'components': {
        'suggest': {
            'label': 'Предложить идею',
            'style': nextcord.ButtonStyle.green
        },
        'approve': {
            'label': 'Одобрить',
            'style': nextcord.ButtonStyle.green
        },
        'deny': {
            'label': 'Отказать',
            'style': nextcord.ButtonStyle.red
        },
        'like': {
            'emoji': '👍',
            'label': '{idea.promotedCount | 0}',
            'style': nextcord.ButtonStyle.gray
        },
        'dislike': {
            'emoji': '👎',
            'label': '{idea.demotedCount | 0}',
            'style': nextcord.ButtonStyle.gray
        },
    },
}


activities_list = [
    {
        'id': 880218394199220334,
        'label': 'Watch Together',
        'max_user': 'Unlimited'
    },
    {
        'id': 1037680572660727838,
        'label': 'Chef Showdown',
        'max_user': '15'
    },
    {
        'id': 1011683823555199066,
        'label': 'Krunker Strike FRVR',
        'max_user': '12'
    },
    {
        'id': 947957217959759964,
        'label': 'Bobble League',
        'max_user': '8'
    },
    {
        'id': 1106787098452832296,
        'label': 'Colonist',
        'max_user': '8'
    },
    {
        'id': 1007373802981822582,
        'label': 'Gartic Phone',
        'max_user': '16'
    },
    {
        'id': 945737671223947305,
        'label': 'Putt Party',
        'max_user': 'Unlimited'
    },
    {
        'id': 832025144389533716,
        'label': 'Blazing 8s',
        'max_user': '8'
    },
    {
        'id': 1070087967294631976,
        'label': 'Whiteboard',
        'max_user': 'Unlimited'
    },
    {
        'id': 1078728822972764312,
        'label': 'Know What I Meme',
        'max_user': '9'
    },
    {
        'id': 902271654783242291,
        'label': 'Sketch Heads',
        'max_user': '16'
    },
    {
        'id': 903769130790969345,
        'label': 'Land-io',
        'max_user': '16'
    },
    {
        'id': 1039835161136746497,
        'label': 'Color Together',
        'max_user': '100'
    },
    {
        'id': 852509694341283871,
        'label': 'SpellCast',
        'max_user': '6'
    },
    {
        'id': 879863686565621790,
        'label': 'Letter League',
        'max_user': '8'
    },
    {
        'id': 832013003968348200,
        'label': 'Checkers In The Park',
        'max_user': 'Unlimited'
    },
    {
        'id': 1107689944685748377,
        'label': 'Bobble Bash',
        'max_user': '8'
    },
    {
        'id': 755827207812677713,
        'label': 'Poker Night',
        'max_user': '25'
    }
]

site_link = "https://lordcord.fun/link-role-callback"
