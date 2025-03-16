from .logs import LogsView
from .role_reaction import RoleReactionView
from .tickets import TicketsView
from .tempvoice import TempVoiceView
from .music import MusicView
from .ideas import IdeasView
from .notification import NotificationView
from .auto_role import AutoRoleView
from .permisson_command import CommandsDataView
from .thread_message import AutoThreadMessage
from .color import ColorView as Color
from .economy import Economy
from .prefix import PrefixView as Prefix
from .languages import Languages
from .reactions import AutoReactions


moduls = {
    'Economy': Economy,
    'Color': Color,
    'Languages': Languages,
    'Prefix': Prefix,
    'TempVoice': TempVoiceView,
    'CommandPermission': CommandsDataView,
    'RoleReactions': RoleReactionView,
    'Music': MusicView,
    'Notification': NotificationView,
    'AutoRoles': AutoRoleView,
    'Reactions': AutoReactions,
    'ThreadMessage': AutoThreadMessage,
    'Tickets': TicketsView,
    'Ideas': IdeasView,
    'Logs': LogsView
}
