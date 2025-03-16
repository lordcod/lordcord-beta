from __future__ import annotations
import asyncio
from collections import deque
import git
import logging
import sys
import os
import aiohttp
import nextcord
import re
from typing import TYPE_CHECKING, Coroutine, List, Optional, Dict, Any

from nextcord.ext import commands

from bot.databases import GuildDateBases
from bot.databases import db
from bot.databases.db import DataBase, establish_connection
from bot.misc.api_site import ApiSite
from bot.misc.ipc_handlers import handlers
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
        engine: DataBase
    invites_data: Dict[int, List[nextcord.Invite]] = {}

    def __init__(
        self,
        *,
        loop: Optional[asyncio.AbstractEventLoop] = None,
        rollout_functions: bool = True,
        allow_bot_command: Optional[bool] = None,
        release_bot: Optional[bool] = None
    ) -> None:
        if allow_bot_command is None:
            allow_bot_command = not release_bot

        if release_bot or get_parser_args().get('api'):
            self.API_URL = 'https://api.lordcord.fun'
        else:
            self.API_URL = 'http://localhost:5000'

        self.release_bot = release_bot
        self.allow_bot_command = allow_bot_command

        intents = nextcord.Intents.all()
        intents.presences = False

        super().__init__(
            loop=loop,
            command_prefix=self.get_command_prefixs,
            intents=intents,
            status=nextcord.Status.idle,
            help_command=None,
            enable_debug_events=True,
            rollout_associate_known=rollout_functions,
            rollout_delete_unknown=rollout_functions,
            rollout_register_new=rollout_functions,
            rollout_update_known=rollout_functions
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
        self.apisite = ApiSite(self, handlers)

        self.twnoti = TwitchNotification(self)
        self.ytnoti = YoutubeNotification(self)

        self.__with_ready__ = self.loop.create_future()
        self.__with_ready_events__ = []

        self.lord_handler_timer: LordTimeHandler = LordTimeHandler(self.loop)

        self.add_listener(self.apisite._ApiSite__run, 'on_ready')
        self.add_listener(self.listen_on_ready, 'on_ready')
        self.add_listener(self.twnoti.parse, 'on_ready')
        self.add_listener(self.ytnoti.parse_youtube, 'on_ready')

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

    async def update_api_config(self) -> bool:
        api = self.apisite
        url = self.API_URL + '/api-config'
        headers = {
            'Authorization': os.environ.get('API_SECRET_TOKEN')
        }
        data = {
            'url': api.callback_url,
            'password': api.password
        }

        async with self.session.post(url, json=data, headers=headers) as response:
            if response.status == 204:
                _log.debug('Successful api update')
                return True
            else:
                _log.warning('Failed api update')
                return False

    async def listen_on_ready(self) -> None:
        if not self.release_bot:
            _log.debug("A test bot has been launched")
        _log.debug('Listen on ready')

        if self.release_bot:
            await self.update_api_config()

        try:
            self.engine = engine = await DataBase.create_engine(os.getenv('POSTGRESQL_DNS'))
        except Exception as exc:
            _log.error("Couldn't connect to the database", exc_info=exc)
            await self.close()
            await self.session.close()
            return

        establish_connection(engine)

        for t in db._tables:
            t.set_engine(engine)
            await t.create()

        if not self.__with_ready__.done():
            self.__with_ready__.set_result(None)

        if not self.release_bot:
            _log.debug('Load started events %d',
                       len(self.__with_ready_events__))

        for event_data in self.__with_ready_events__:
            self.dispatch(event_data[0], *event_data[1], **event_data[2])

    def dispatch(self, event_name: str, *args: Any, **kwargs: Any) -> None:
        if not self.__with_ready__.done() and event_name.lower() != 'ready':
            self.__with_ready_events__.append((event_name, args, kwargs))
            return
        return super().dispatch(event_name, *args, **kwargs)
