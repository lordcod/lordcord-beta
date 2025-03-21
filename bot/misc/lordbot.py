from __future__ import annotations
import asyncio
from collections import deque
import git
import logging
import os
import aiohttp
import nextcord
import re
from aiohttp_socks import ProxyConnector
from typing import TYPE_CHECKING, Coroutine, List, Optional, Dict

from nextcord.ext import commands
from tortoise import Tortoise

from bot.databases import GuildDateBases
from bot.misc.sites.vk_site import VkSite
from bot.resources.info import DEFAULT_PREFIX
from bot.misc.utils import LordTimeHandler, get_parser_args
from bot.languages import i18n
from bot.misc.noti import TwitchNotification, YoutubeNotification

_log = logging.getLogger(__name__)


def get_shard_list(shard_ids: str):
    res = []
    for shard in shard_ids.split(","):
        if data := re.fullmatch(r"(\d+)-(\d+)", shard):
            res.extend(range(int(data.group(1)),
                             int(data.group(2))))
        else:
            res.append(int(shard))
    return res


class LordBot(commands.AutoShardedBot):
    if TYPE_CHECKING:
        release_sha: str
        release_date: int
        release_tag: str
        API_URL: str

    invites_data: Dict[int, List[nextcord.Invite]] = {}

    def __init__(
        self,
        *,
        loop: Optional[asyncio.AbstractEventLoop] = None,
        chunk_guilds_at_startup: bool = True,
        bot_command: Optional[bool] = None,
        release: Optional[bool] = None
    ) -> None:
        if bot_command is None:
            allow_bot_command = not release

        if release or get_parser_args().get('api'):
            self.API_URL = 'https://api.lordcord.fun'
        else:
            self.API_URL = 'http://localhost:5000'

        self.release = release
        self.allow_bot_command = allow_bot_command

        intents = nextcord.Intents.all()
        intents.presences = False

        proxy_url = os.getenv('PROXY')
        if proxy_url:
            connector = ProxyConnector.from_url(proxy_url, loop=loop)
        else:
            connector = None

        super().__init__(
            loop=loop,
            command_prefix=self.get_command_prefixs,
            intents=intents,
            status=nextcord.Status.idle,
            chunk_guilds_at_startup=chunk_guilds_at_startup,
            help_command=None,
            enable_debug_events=True,
            connector=connector
        )

        _messages = deque(
            self._connection._messages,
            maxlen=None
        )
        self._connection._messages = _messages
        self._connection.max_messages = None

        self.load_i18n_config()
        self.get_git_info()

        self.activity = nextcord.CustomActivity(
            name=f'{DEFAULT_PREFIX}help | {self.release_tag}')

        self.__session = None

        self.vk_site = VkSite(self)
        self.twnoti = TwitchNotification(self)
        self.ytnoti = YoutubeNotification(self)

        self.lord_handler_timer: LordTimeHandler = LordTimeHandler(self.loop)

        self.add_listener(self.listen_on_connect, 'on_connect')
        self.loop.create_task(self.vk_site.run())
        self.loop.create_task(self.twnoti.parse())
        self.loop.create_task(self.ytnoti.parse_youtube())

    def get_git_info(self):
        repo = git.Repo(search_parent_directories=True)

        self.release_sha = repo.head.object.hexsha[:8]
        self.release_date = repo.head.object.committed_date
        tags_dt = {tag.commit.committed_date: tag for tag in repo.tags}
        self.release_tag = tags_dt[max(tags_dt)].name

    def load_i18n_dir(self, dirname: str) -> None:
        for filename in os.listdir(dirname):
            path = os.path.join(dirname, filename)
            if os.path.isdir(path):
                self.load_i18n_dir(path)
            if not os.path.isfile(path) or not filename.endswith('.json'):
                continue
            data = i18n._parse_json(i18n._load_file(path))
            i18n.parser(data)

    def load_i18n_config(self) -> None:
        i18n.config['locale'] = 'en'
        i18n.from_file("./bot/languages/localization_any.json")

        temps_dir = './bot/languages/temp'
        self.load_i18n_dir(temps_dir)
        _log.trace('The i18n config is loaded')

    @property
    def session(self) -> aiohttp.ClientSession:
        session = self.http._HTTPClient__session
        if session is None or session.closed:
            return session

        if self.__session is None or self.__session.closed:
            self.__session = aiohttp.ClientSession()

        return self.__session

    async def process_commands(self, message: nextcord.Message) -> None:
        """|coro|

        This function processes the commands that have been registered
        to the bot and other groups. Without this coroutine, none of the
        commands will be triggered.

        By default, this coroutine is called inside the :func:`.on_message`
        event. If you choose to override the :func:`.on_message` event, then
        you should invoke this coroutine as well.

        This is built using other low level tools, and is equivalent to a
        call to :meth:`~.Bot.get_context` followed by a call to :meth:`~.Bot.invoke`.

        This also checks if the message's author is a bot and doesn't
        call :meth:`~.Bot.get_context` or :meth:`~.Bot.invoke` if so.

        Parameters
        ----------
        message: :class:`nextcord.Message`
            The message to process commands for.
        """
        if not self.allow_bot_command and message.author.bot:
            return

        ctx = await self.get_context(message)
        await self.invoke(ctx)

    @staticmethod
    async def get_command_prefixs(
        bot: commands.Bot,
        msg: nextcord.Message
    ) -> List[str]:
        "Returns a list of prefixes that can be used when using bot commands"
        if msg.guild is None:
            return [DEFAULT_PREFIX, f"<@{bot.user.id}> ", f"<@!{bot.user.id}> "]
        gdb = GuildDateBases(msg.guild.id)
        prefix = await gdb.get('prefix', DEFAULT_PREFIX)
        return [prefix, f"<@{bot.user.id}> ", f"<@!{bot.user.id}> "]

    def set_event(self, coro: Coroutine, name: Optional[str] = None) -> None:
        """A decorator that registers an event to listen to.

        You can find more info about the events on the :ref:`documentation below <discord-api-events>`.

        The events must be a :ref:`coroutine <coroutine>`, if not, :exc:`TypeError` is raised

        Raises
        ------
        TypeError
            The coroutine passed is not actually a coroutine.

        Example
        -------

        .. code-block:: python3

            async def on_ready(): pass
            async def my_message(message): pass

            bot.set_event(on_ready)
            bot.set_event(my_message, 'on_message')
        """

        if not asyncio.iscoroutinefunction(coro):
            raise TypeError("event registered must be a coroutine function")

        name = name or coro.__name__

        setattr(self, name, coro)

    async def listen_on_connect(self) -> None:
        if not self.release:
            _log.debug("A test bot has been launched")
        _log.debug('Listen on connect')

        try:
            await Tortoise.init(
                db_url="sqlite://db/.sqlite3",
                modules={'models': ['bot.databases.models']},
            )
            await Tortoise.generate_schemas()
        except Exception as exc:
            _log.error("Couldn't connect to the database", exc_info=exc)
            await self.close()
            await self.session.close()
            return
        else:
            _log.debug('Database is ready')
