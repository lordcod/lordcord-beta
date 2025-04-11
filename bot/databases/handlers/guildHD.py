from __future__ import annotations
from collections import defaultdict
import functools
import logging
from typing import Any, Optional
from ..models import GuildModel

_log = logging.getLogger(__name__)


cache = defaultdict(dict)


def check_registration(func):
    @functools.wraps(func)
    async def wrapped(self: GuildDateBases, *args, **kwargs):
        await self.register()
        return await func(self, *args, **kwargs)
    return wrapped


class AwaitableGDBGet:
    def __init__(
        self,
        gdb: GuildDateBases,
        service: str,
        default: Any
    ):
        self.gdb = gdb
        self.service = service
        self.default = default
        self.operations = []

    def __getattr__(self, *args, **kwargs):
        self.operations.append(('__getattr__', args, kwargs))
        return self

    def __call__(self, *args, **kwds):
        self.operations.append(('__call__', args, kwds))
        return self

    async def submit(self):
        await self.gdb.register()

        data = getattr(self.gdb.guild, self.service, self.default)
        cache[self.gdb.guild_id][self.service] = data

        for name, args, kwds in self.operations:
            if name == '__getattr__':
                data = getattr(data, *args, **kwds)
            if name == '__call__':
                data = data(*args, **kwds)

        return data

    def __await__(self):
        return self.submit().__await__()


class GuildDateBases:
    guild: GuildModel

    def __init__(self, guild_id: int) -> None:
        self.guild_id = guild_id

    async def register(self) -> bool:
        self.guild, ok = await GuildModel.get_or_create(id=self.guild_id)
        return ok

    def get(self, service: str, default: Any = None) -> AwaitableGDBGet:
        return AwaitableGDBGet(self, service, default)

    def get_cache(self, service: str, default: Any = None) -> Any:
        return cache[self.guild_id].get(service, default)

    @check_registration
    async def set(self, service, value):
        setattr(self.guild, service, value)
        await self.guild.save()

    @check_registration
    async def set_on_json(self, service, key, value):
        data: Optional[dict] = await self.get(service)

        if not data:
            data = {}

        data[key] = value
        await self.set(service, data)

    @check_registration
    async def append_on_json(self, service, value):
        data: Optional[list] = await self.get(service)

        if not data:
            data = []

        data.append(value)
        await self.set(service, data)

    async def delete(self):
        await self.guild.delete()

    def __eq__(self, value: object) -> bool:
        return (isinstance(value, GuildDateBases)
                and value.guild_id == self.guild_id)

    def __hash__(self) -> int:
        return self.guild_id
