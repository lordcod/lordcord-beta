from __future__ import annotations
import functools
import logging
from tkinter import NO
from typing import Any, Optional


from ..models import EconomicModel
from tortoise.functions import Sum

reserved: dict[int, list[int]] = {}
tasks = []
_log = logging.getLogger(__name__)


def check_registration(func):
    @functools.wraps(func)
    async def decorator(self: EconomyMemberDB, *args, **kwargs):
        await self.register()
        return await func(self, *args, **kwargs)
    return decorator


class EconomyMemberDB:
    economic: EconomicModel

    def __init__(self, guild_id: int, member_id: int = None) -> None:
        self.guild_id = guild_id
        self.member_id = member_id

    async def register(self) -> None:
        self.economic, ok = await EconomicModel.get_or_create(
            guild_id=self.guild_id,
            member_id=self.member_id
        )

    async def get_leaderboards(self):
        economics = (
            await EconomicModel
            .filter(guild_id=self.guild_id)
            .annotate(total=Sum('bank', 'balance'))
            .order_by('total')
        )

        return [(eco.member_id, eco.balance, eco.bank, eco.balance+eco.bank) for eco in economics]

    @check_registration
    async def get_service(self, service: str):
        return getattr(self.economic, service)

    @check_registration
    async def update(self, arg: str, value: Any):
        setattr(self.economic, arg, value)
        await self.economic.save()

    @check_registration
    async def update_dict(self, data: Optional[dict] = None, **kwargs: Any):
        if data is not None and len(kwargs) > 0:
            raise TypeError("You can't use kwargs in conjunction with data")
        await self.economic.update_from_dict(data or kwargs).save()

    @check_registration
    async def delete(self):
        await self.economic.delete()

    async def delete_guild(self):
        await EconomicModel.filter(guild_id=self.guild_id).delete()

    async def get(self, __name, __default=None):
        data = await self.get_service(__name)
        return data or __default

    async def set(self, key, value):
        await self.update(key, value)

    @check_registration
    async def increment(self, key, value):
        setattr(self.economic, key, getattr(self.economic, key)+value)
        await self.economic.save()

    @check_registration
    async def decline(self, key, value):
        setattr(self.economic, key, getattr(self.economic, key)-value)
        await self.economic.save()

    @staticmethod
    async def increment_for_ids(guild_id, member_ids, key, value):
        pass

    @staticmethod
    async def decline_for_ids(guild_id, member_ids, key, value):
        pass
