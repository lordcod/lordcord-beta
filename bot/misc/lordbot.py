from __future__ import annotations
import asyncio
from collections import deque
import aiogram
import git
import logging
import os
import aiohttp
import nextcord
import re
from aiohttp_socks import ProxyConnector
from typing import TYPE_CHECKING, Any, Coroutine, List, Optional, Dict

from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from nextcord.ext import commands
from tortoise import Tortoise
from cordlog import setup_storage

from bot.databases import GuildDateBases
from bot.misc.env import API_URL, PROXY, TELEGRAM_TOKEN, LOG_WEBHOOK
from bot.misc.sites.site import ApiSite
from bot.resources.info import DEFAULT_PREFIX, SITE
from bot.misc.utils import LordTimeHandler
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

        self.SITE_URL = SITE
        self.API_URL = API_URL

        self.release = release
        self.allow_bot_command = allow_bot_command

        intents = nextcord.Intents.all()
        intents.presences = False

        if proxy_url := PROXY:
            connector = ProxyConnector.from_url(
                proxy_url, loop=loop)
        else:
            connector = None
            _log.trace('Proxy %s, %s', proxy_url, connector)

        super().__init__(
            loop=loop,
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
        self.__send_api_state = None
        self.__wait_api_state = None

        self.api_site = ApiSite(self)
        self.twnoti = TwitchNotification(self)
        self.ytnoti = YoutubeNotification(self)
        if TELEGRAM_TOKEN:
            self.telegram_client = aiogram.Bot(
                TELEGRAM_TOKEN,
                default=DefaultBotProperties(parse_mode=ParseMode.HTML)
            )
        else:
            self.telegram_client = None

        self.lord_handler_timer: LordTimeHandler = LordTimeHandler(
            self.loop)

        self.add_listener(self.listen_on_connect, 'on_connect')
        self.add_listener(self.listen_on_ready, 'on_ready')
        self.loop.create_task(self.api_site.run())

    async def wait_api_state(self, state: str, timeout: Optional[int] = None) -> bool:
        return await self.__wait_api_state(state, timeout=timeout)

    async def send_api_state(self, state: str, data: Any) -> bool:
        return await self.__send_api_state(state, data)

    def _set_callback_api_state(self, send, wait):
        self.__send_api_state = send
        self.__wait_api_state = wait

    def get_git_info(self):
        repo = git.Repo(search_parent_directories=True)

        self.release_sha = repo.head.object.hexsha[:8]
        self.release_date = repo.head.object.committed_date
        tags_dt = {tag.commit.committed_date: tag for tag in repo.tags}
        self.release_tag = tags_dt[max(tags_dt)].name

    def load_i18n_dir(self, dirname: str) -> None:
        if not os.path.exists(dirname) or self.release:
            return

        for filename in os.listdir(dirname):
            path = os.path.join(dirname, filename)
            if os.path.isdir(path):
                self.load_i18n_dir(path)
            if not os.path.isfile(path) or not filename.endswith('.json'):
                continue

            args = filename.split('.')
            locale = args[-2] if len(args) > 2 else None
            _log.trace('Load temp file languages %s, locale %s',
                       filename, locale)

            data = i18n._parse_json(i18n._load_file(path))
            i18n.parser(data, locale)

    def load_i18n_config(self) -> None:
        i18n.config['locale'] = 'en'
        i18n.from_file("./bot/languages/localization.json")

        temps_dir = './bot/languages/temp'
        self.load_i18n_dir(temps_dir)
        _log.trace('The i18n config is loaded')

    @property
    def session(self) -> aiohttp.ClientSession:
        session = self.http._HTTPClient__session
        if session is not None and not session.closed:
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

    async def get_prefix(self, msg: nextcord.Message):
        "Returns a list of prefixes that can be used when using bot commands"
        mentions_prefix = [f"<@{self.user.id}> ", f"<@!{self.user.id}> "]
        if msg.guild is None:
            return [DEFAULT_PREFIX, *mentions_prefix]

        gdb = GuildDateBases(msg.guild.id)
        prefix = await gdb.get('prefix', DEFAULT_PREFIX)
        return [prefix, *mentions_prefix]

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

    async def listen_on_ready(self) -> None:
        self.loop.create_task(self.twnoti.parse())
        self.loop.create_task(self.ytnoti.parse())

    async def listen_on_connect(self) -> None:
        setup_storage(
            webhook_url=LOG_WEBHOOK,
            session=self.session
        )
        
        if self.release:
            _log.info("[PROD MODE] Start")
        else:
            _log.info("[DEV MODE] Start")

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
