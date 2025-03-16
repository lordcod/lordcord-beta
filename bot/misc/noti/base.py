from __future__ import annotations

import asyncio
import time
import logging
from typing import TYPE_CHECKING, Any, Generic, Optional, TypeVar

from aiohttp import ClientConnectionError


if TYPE_CHECKING:
    from bot.misc.lordbot import LordBot

T = TypeVar('T')
_log = logging.getLogger(__name__)


class NotificationApi:
    if TYPE_CHECKING:
        bot: LordBot

    def __init__(self, bot: LordBot) -> None:
        self.bot: LordBot = bot

    async def request(self, method: str, url: str, **kwargs) -> Any:
        exception: Optional[Exception] = None

        for _ in range(3):
            try:
                async with self.bot.session.request(method, url, **kwargs) as response:
                    content_type = response.headers.get('Content-Type')
                    if content_type == 'application/json' or 'application/json' in content_type:
                        data = await response.json()
                    else:
                        data = await response.read()
            except (asyncio.TimeoutError, ClientConnectionError) as exc:
                _log.debug('Temporary error in the request', exc_info=exc)
                exception = exc
            except Exception as exc:
                _log.error('It was not possible to get data from the api', exc_info=exc)
                exception = exc

            if response.ok:
                return data
            else:
                try:
                    response.raise_for_status()
                except Exception as exc:
                    _log.error('It was not possible to get data from the api, status: %s, data: %s', response.status, data, exc_info=exc)
                    exception = exc

            await asyncio.sleep(30)

        if exception is not None:
            raise exception from None


class Notification(Generic[T]):
    if TYPE_CHECKING:
        bot: LordBot
        api: T
        heartbeat_timeout: int
        last_heartbeat: int
        _running: bool

    def __init__(
        self,
        bot: LordBot,
        api: T,
        heartbeat_timeout: int = 180
    ) -> None:
        self.bot: LordBot = bot
        self.api: T = api
        self.heartbeat_timeout: int = heartbeat_timeout

        self.last_heartbeat = 0
        self._running = False

    @property
    def running(self) -> bool:
        return self._running and self.last_heartbeat > time.time() - self.heartbeat_timeout

    @running.setter
    def running(self, __value: bool) -> None:
        if not isinstance(__value, bool):
            raise TypeError('The %s type is not supported' % (type(__value).__name__,))
        self._running = __value

    async def parse(self) -> None:
        raise NotImplementedError
