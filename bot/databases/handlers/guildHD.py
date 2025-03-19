from __future__ import annotations
from collections import defaultdict
import functools
import logging
from typing import Any, Optional
from ..models import GuildModel
from ..misc.error_handler import on_error

_log = logging.getLogger(__name__)


cache = defaultdict(dict)


def check_registration(func):
    @functools.wraps(func)
    async def wrapped(self: GuildDateBases, *args, **kwargs):
        await self.register()
        return await func(self, *args, **kwargs)
    return wrapped


class GuildDateBases:
    guild: GuildModel

    def __init__(self, guild_id: int) -> None:
        self.guild_id = guild_id

    @on_error()
    async def register(self):
        self.guild, ok = await GuildModel.get_or_create(id=self.guild_id)

    @on_error()
    @check_registration
    async def get(self, service: str, default: Any = None) -> Any:
        data = getattr(self.guild, service, default)
        cache[self.guild_id][service] = data
        return data

    def get_cache(self, service: str, default: Any = None) -> Any:
        return cache[self.guild_id].get(service, default)

    @check_registration
    @on_error()
    async def set(self, service, value):
        setattr(self.guild, service, value)
        await self.guild.save()

    @check_registration
    @on_error()
    async def set_on_json(self, service, key, value):
        data: Optional[dict] = await self.get(service)

        if not data:
            data = {}

        data[key] = value
        await self.set(service, data)

    @check_registration
    @on_error()
    async def append_on_json(self, service, value):
        data: Optional[list] = await self.get(service)

        if not data:
            data = []

        data.append(value)
        await self.set(service, data)

    @on_error()
    async def delete(self):
        await self.guild.delete()

    def __eq__(self, value: object) -> bool:
        return (isinstance(value, GuildDateBases)
                and value.guild_id == self.guild_id)

    def __hash__(self) -> int:
        return self.guild_id
