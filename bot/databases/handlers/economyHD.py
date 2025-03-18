from __future__ import annotations
import contextlib
import functools
import logging

from ..misc.error_handler import on_error

reserved: dict[int, list[int]] = {}
tasks = []
_log = logging.getLogger(__name__)


def check_registration(func):
    @functools.wraps(func)
    async def decorator(self: EconomyMemberDB, *args, **kwargs):
        reserved.setdefault(self.guild_id, [])
        if self.member_id not in reserved[self.guild_id]:
            reserved[self.guild_id].append(self.member_id)
            await self.register()
        return await func(self, *args, **kwargs)
    return decorator


class EconomyMemberDB:
    def __init__(self, guild_id: int, member_id: int = None) -> None:
        self.guild_id = guild_id
        self.member_id = member_id


engine = None
adapt_array = None


class _EconomyMemberDB:
    def __init__(self, guild_id: int, member_id: int = None) -> None:
        self.guild_id = guild_id
        self.member_id = member_id

    async def register(self) -> None:

        data = await self._get()

        val = (self.guild_id, self.member_id)

        if data is None and val not in tasks:
            tasks.append(val)
            await self.insert()
            tasks.remove(val)

    @on_error()
    async def get_leaderboards(self):
        leaderboard = await engine.fetchall(
            """SELECT member_id, balance, bank, balance+bank as total
                FROM economic
                WHERE guild_id = %s
                ORDER BY total DESC""",
            (self.guild_id,)
        )

        return leaderboard

    @on_error()
    async def get_service(self, service: str):
        data = await engine.fetchvalue(
            'SELECT ' + service + ' FROM economic WHERE guild_id = %s AND member_id = %s',
            (self.guild_id, self.member_id)
        )

        return data

    @on_error()
    async def update(self, arg, value):
        await engine.execute(f'UPDATE economic SET {arg} = %s WHERE guild_id = %s AND member_id = %s', (
            value, self.guild_id, self.member_id))

    @on_error()
    @check_registration
    async def update_list(self, args: dict):
        keys = ', '.join(
            [f"{a} = %s" for a in args.keys()])
        values = [*args.values(), self.guild_id, self.member_id]
        await engine.execute(
            f'UPDATE economic SET {keys} WHERE guild_id = %s AND member_id = %s', values)

    @on_error()
    @check_registration
    async def delete(self):
        with contextlib.suppress(IndexError):
            reserved[self.guild_id].pop(self.member_id)
        await engine.execute(
            'DELETE FROM economic WHERE guild_id = %s AND member_id = %s', (self.guild_id, self.member_id))

    @on_error()
    @check_registration
    async def delete_guild(self):
        reserved.pop(self.guild_id, None)
        await engine.execute(
            'DELETE FROM economic WHERE guild_id = %s', (self.guild_id,))

    @check_registration
    async def get(self, __name, __default=None):
        data = await self.get_service(__name)
        return data or __default

    @check_registration
    async def set(self, key, value):
        await self.update(key, value)

    @check_registration
    async def increment(self, key, value):
        await engine.execute(f"""UPDATE economic SET {key} = {key} + %s
                                 WHERE guild_id = %s
                                 AND member_id = %s""", (
            value, self.guild_id, self.member_id))

    @check_registration
    async def decline(self, key, value):
        await engine.execute(f"""UPDATE economic SET {key} = {key} - %s
                                 WHERE guild_id = %s
                                 AND member_id = %s""", (
            value, self.guild_id, self.member_id))

    @on_error()
    @staticmethod
    async def increment_for_ids(guild_id, member_ids, key, value):
        dmis = adapt_array(member_ids)
        await engine.execute(f"""UPDATE economic SET {key} = {key} + %s
                                 WHERE guild_id = %s
                                 AND (SELECT ARRAY[member_id] && %s::bigint[])""", (
            value, guild_id, dmis))

    @on_error()
    @staticmethod
    async def decline_for_ids(guild_id, member_ids, key, value):
        dmis = adapt_array(member_ids)
        await engine.execute(f"""UPDATE economic SET {key} = {key} - %s
                                 WHERE guild_id = %s
                                 AND (SELECT ARRAY[member_id] && %s::bigint[])""", (
            value, guild_id, dmis))
