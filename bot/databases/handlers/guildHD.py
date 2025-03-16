from __future__ import annotations
from collections import defaultdict
import contextlib
import functools
import logging
import time
from typing import Any, Dict, List, Optional, Union, TypeVar

from numpy import isin


from ..db_engine import DataBase
from ..misc.error_handler import on_error

_log = logging.getLogger(__name__)


class GuildCache:
    def __init__(self, timeout: int) -> None:
        self._cache = defaultdict(dict)
        self._timeout = timeout

    def set(self, guild_id, key, value) -> None:
        self._cache[guild_id][key] = (time.time()+self._timeout, value)

    def is_rate_limited(self, guild_id, key) -> Any:
        with contextlib.suppress(KeyError):
            timestamp, _ = self._cache[guild_id][key]
            if timestamp > time.time():
                return True
        return False

    def get_hash(self, guild_id, key) -> Any:
        with contextlib.suppress(KeyError):
            _, value = self._cache[guild_id][key]
            return value

    def set_hash(self, guild_id, key, value) -> None:
        timestamp = None
        with contextlib.suppress(KeyError):
            timestamp, _ = self._cache[guild_id][key]
        self._cache[guild_id][key] = (timestamp or 0, value)


engine: DataBase = None
reserved = []
cache = GuildCache(timeout=10)
seat_cache = GuildCache(timeout=60)
settings_limits = ('score_state', 'message_state', )
collectable_hashable_data: List[str] = ['language', 'color']
hashable_data: Dict[int, Dict[str, Any]] = defaultdict(dict)
T = TypeVar("T")


def check_registration(func):
    @functools.wraps(func)
    async def wrapped(self: GuildDateBases, *args, **kwargs):
        await self.register()
        return await func(self, *args, **kwargs)
    return wrapped


class GuildDateBases:
    def __init__(self, guild_id: int) -> None:
        self.guild_id = guild_id

    @on_error()
    async def register(self):
        if self.guild_id in reserved:
            return
        reserved.append(self.guild_id)
        if not await self._exists(self.guild_id):
            await self._insert(self.guild_id)
            _log.trace(f"Guild {self.guild_id} registration completed")

    @on_error()
    async def _exists(self, guild_id):
        return await engine.fetchone(
            'SELECT EXISTS (SELECT true FROM guilds WHERE id=%s);', (guild_id,))

    @on_error()
    async def _get(self, guild_id):
        guild = await engine.fetchone(
            'SELECT * FROM guilds WHERE id = %s', (guild_id,))

        return guild

    @on_error()
    async def _get_service(self, guild_id, arg):
        value = await engine.fetchvalue(
            'SELECT ' + arg + ' FROM guilds WHERE id = %s', (guild_id,))

        return value

    @on_error()
    async def _insert(self, guild_id):
        await engine.execute('INSERT INTO guilds (id) VALUES (%s)', (guild_id,))

    @on_error()
    @check_registration
    async def get(self, service: str, default: T | None = None) -> Union[T, Any]:
        if cache.is_rate_limited(self.guild_id, service):
            return cache.get_hash(self.guild_id, service)

        if service in settings_limits and seat_cache.is_rate_limited(self.guild_id, service):
            return cache.get_hash(self.guild_id, service)

        data = await self._get_service(self.guild_id, service)

        if data is None:
            return default

        cache.set(self.guild_id, service, data)

        return data

    def get_hash(self, service: str, default: T | None = None) -> Union[T, Any]:
        data = cache.get_hash(self.guild_id, service)
        if data is None:
            return default
        return data

    @check_registration
    @on_error()
    async def set(self, service, value):
        cache.set_hash(self.guild_id, service, value)

        if service in settings_limits:
            if seat_cache.is_rate_limited(self.guild_id, service):
                return
            seat_cache.set(self.guild_id, service, True)

        await engine.execute(
            'UPDATE guilds SET ' + service + ' = %s WHERE id = %s', (value,
                                                                     self.guild_id))

    @check_registration
    @on_error()
    async def set_on_json(self, service, key, value):
        data: Optional[dict] = await self.get(service)

        if not data:  # type: ignore
            data = {}

        data[key] = value
        await self.set(service, data)

    @check_registration
    @on_error()
    async def append_on_json(self, service, value):
        data: Optional[list] = await self.get(service)

        if not data:  # type: ignore
            data = []

        data.append(value)
        await self.set(service, data)

    @on_error()
    async def delete(self):
        reserved.pop(self.guild_id, None)

        await engine.execute('DELETE FROM guilds WHERE id = %s',
                             (self.guild_id,))

    @on_error()
    @staticmethod
    async def get_all(service: str, *, not_null: bool = False) -> Union[T, Any]:
        if not isinstance(service, str):
            raise TypeError
        return await engine.fetchall(
            'SELECT id, ' + service + ' FROM guilds'
            + (' WHERE ' + service + ' IS NOT NULL' if not_null else '')
        )

    @on_error()
    @staticmethod
    async def get_deleted():
        return await engine.fetchall('SELECT id, delete_task FROM guilds WHERE delete_task IS NOT NULL')

    def __eq__(self, value: object) -> bool:
        return isinstance(value, GuildDateBases) and value.guild_id == self.guild_id

    def __hash__(self) -> int:
        return self.guild_id
