from __future__ import annotations

import asyncio
from collections import defaultdict
import os
import time
import logging
from typing import TYPE_CHECKING, Dict, Optional, Set, Tuple
from aiohttp.web_exceptions import HTTPUnauthorized

from bot.databases.handlers.guildHD import GuildDateBases
from bot.databases.models import GuildModel, Q
from bot.misc.env import TWITCH_CLIENT_ID, TWITCH_CLIENT_SECRET
from bot.misc.noti.base import Notification, NotificationApi
from bot.misc.utils import get_payload, generate_message, lord_format
from bot.resources.info import DEFAULT_TWITCH_MESSAGE

try:
    from .types import Stream, User
except ImportError:
    from bot.misc.noti.twitch.types import Stream, User

if TYPE_CHECKING:
    from bot.misc.lordbot import LordBot

_log = logging.getLogger(__name__)


def refresh_token(func):
    if isinstance(func, staticmethod):
        func = func.__func__

    async def wrapped(self: TwNotiAPI, *args, **kwargs):
        try:
            return await func(self, *args, **kwargs)
        except HTTPUnauthorized:
            await self.get_oauth_token()
            raise
    return wrapped


class TwCache:
    if TYPE_CHECKING:
        usernames: Set[str]
        twitch_streaming: Set[str]
        user_info: Dict[str, User]
        directed_data: Dict[str, Set[int]]

    def __init__(self) -> None:
        self.usernames: Set[str] = set()
        self.twitch_streaming: Set[str] = set()
        self.user_info: Dict[str, User] = dict()
        self.directed_data: Dict[str, Set[int]] = defaultdict(set)


class TwNotiAPI(NotificationApi):
    twitch_api_access_token: Optional[str] = None
    twitch_api_access_token_end: Optional[int] = None

    if TYPE_CHECKING:
        cache: TwCache
        client_id: str
        client_secret: str

    def __init__(
        self,
        bot: LordBot,
        cache: TwCache,
        client_id: str,
        client_secret: str
    ) -> None:
        super().__init__(bot)
        self.cache = cache
        self.client_id: str = client_id
        self.client_secret: str = client_secret

    async def check_token(self) -> None:
        if self.twitch_api_access_token is None or time.time() > self.twitch_api_access_token_end:
            try:
                await self.get_oauth_token()
            except Exception as exc:
                _log.warning('The token could not be obtained', exc_info=exc)
                raise

    async def get_oauth_token(self) -> None:
        url = 'https://id.twitch.tv/oauth2/token'
        data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'grant_type': 'client_credentials'
        }
        json = await self.request('POST', url,  data=data)
        self.twitch_api_access_token_end = json['expires_in']+time.time()
        self.twitch_api_access_token = json['access_token']

    @refresh_token
    async def get_user_info(self, username: str) -> Optional[User]:
        await self.check_token()

        url = 'https://api.twitch.tv/helix/users'
        params = {
            'login': username
        }
        headers = {
            'Client-ID': self.client_id,
            'Authorization': 'Bearer ' + self.twitch_api_access_token
        }
        data = await self.request('GET', url, params=params, headers=headers)

        if data is not None and len(data['data']) > 0:
            user = User(**data['data'][0])
            self.cache.user_info[username] = user
            return user

    @refresh_token
    async def is_streaming(self, username: str) -> Tuple[bool, Optional[Stream]]:
        await self.check_token()

        url = 'https://api.twitch.tv/helix/streams'
        params = {
            'user_login': username
        }
        headers = {
            'Client-ID': self.client_id,
            'Authorization': 'Bearer ' + self.twitch_api_access_token
        }
        data = await self.request('GET', url, params=params, headers=headers)

        if data is not None and len(data['data']) > 0:
            return True, Stream(**data['data'][0])
        else:
            return False, None


class TwNoti(Notification[TwNotiAPI], TwCache):
    def __init__(
        self,
        bot: LordBot,
        client_id: str = TWITCH_CLIENT_ID,
        client_secret: str = TWITCH_CLIENT_SECRET
    ) -> None:
        TwCache.__init__(self)
        Notification.__init__(self, bot=bot, api=TwNotiAPI(
            bot, self, client_id, client_secret))

    async def callback_on_start(self, stream: Stream):
        _log.debug('%s started stream', stream.user_login)

        if stream.user_login not in self.user_info:
            user = await self.api.get_user_info(stream.user_login)
        else:
            user = self.user_info[stream.user_login]

        for gid in self.directed_data[stream.user_login]:
            guild = self.bot.get_guild(gid)
            gdb = GuildDateBases(gid)
            twitch_data = await gdb.get('twitch_notification')
            for id, data in twitch_data.items():
                if data['username'] == stream.user_login:
                    channel = self.bot.get_channel(data['channel_id'])
                    payload = get_payload(
                        guild=guild, stream=stream, user=user)
                    mes_data = generate_message(lord_format(
                        data.get('message', DEFAULT_TWITCH_MESSAGE), payload))
                    await channel.send(**mes_data)

    async def callback_on_stop(self, username: str): ...

    async def add_channel(self, guild_id: int, username: str) -> None:
        if username not in self.usernames:
            with_started, _ = await self.api.is_streaming(username)
            if with_started:
                self.twitch_streaming.add(username)
            self.usernames.add(username)
        self.directed_data[username].add(guild_id)

    async def parse(self) -> None:
        if self._running:
            return

        if self.api.client_id is None or self.api.client_secret is None:
            _log.error(
                "[Twitch Notification] It was not possible to get tokens for authorization")
            return

        _log.debug('Started twitch parsing')

        gms = await GuildModel.filter(~Q(twitch_notification={}))
        _log.trace('ALL DATA %s', gms)
        for gm in gms:
            for data in gm.twitch_notification.values():
                _log.trace('LOAD DATA %s %s', gm.id, data)
                await self.add_channel(gm.id, data['username'])

        for uid in self.usernames:
            with_started, _ = await self.api.is_streaming(uid)
            if with_started:
                self.twitch_streaming.add(uid)

        self._running = True
        while True:
            await asyncio.sleep(self.heartbeat_timeout)
            if not self._running:
                break
            self.last_heartbeat = time.time()

            tasks = []
            for uid in self.usernames:
                try:
                    with_started, data = await self.api.is_streaming(uid)
                except Exception as exp:
                    _log.error('An error was received when executing the request (%s)',
                               uid,
                               exc_info=exp)
                    continue

                if with_started and uid not in self.twitch_streaming:
                    self.twitch_streaming.add(uid)
                    tasks.append(self.callback_on_start(data))
                if not with_started and uid in self.twitch_streaming:
                    self.twitch_streaming.remove(uid)
                    tasks.append(self.callback_on_stop(uid))

                _log.trace(
                    'Data about the user %s has been received: %s %s', uid, with_started, data)
            await asyncio.gather(*tasks)

        _log.debug('Parsing %s ending', type(self).__name__)
