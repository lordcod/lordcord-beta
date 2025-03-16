from __future__ import annotations
import nextcord
from typing import Optional

from bot.databases.misc.simple_task import to_task
from ..db_engine import DataBase
from ..misc.error_handler import on_error

engine: DataBase = None


class RoleDateBases:
    def __init__(
        self,
        guild_id: Optional[int] = None,
        member_id: Optional[int] = None
    ) -> None:
        self.guild_id = guild_id
        self.member_id = member_id

    @on_error()
    async def get_all(self):
        data = await engine.fetchall('SELECT guild_id, member_id, role_id, time FROM roles')
        return data

    @on_error()
    async def get_as_guild(self):
        data = await engine.fetchall(
            ('SELECT member_id, role_id, time '
             'FROM roles WHERE guild_id = %s AND (system IS NULL OR system = FALSE)'),
            [self.guild_id])

        return data

    @on_error()
    async def get_as_member(self):
        data = await engine.fetchall(
            ('SELECT member_id, role_id, time FROM roles '
             'WHERE guild_id = %s AND member_id = %s AND (system IS NULL OR system = FALSE)'),
            (self.guild_id, self.member_id)
        )

        return data

    @on_error()
    async def get_as_role(self, role_id: int):
        data = await engine.fetchone(
            ('SELECT time FROM roles '
             'WHERE guild_id = %s AND member_id = %s AND role_id = %s AND (system IS NULL OR system = FALSE)'),
            (self.guild_id, self.member_id, role_id)
        )

        return data

    @on_error()
    async def get_system(self):
        data = await engine.fetchall(
            ('SELECT member_id, role_id, time FROM roles '
             'WHERE guild_id = %s AND member_id = %s AND system = TRUE'),
            (self.guild_id, self.member_id)
        )

        return data

    @on_error()
    async def insert(self, role_id: int, time: int):
        await engine.execute(
            ('INSERT INTO roles '
             '(guild_id, member_id, role_id, time) '
             'VALUES (%s, %s, %s, %s)'),
            (self.guild_id, self.member_id, role_id, time)
        )

    @on_error()
    async def update(self, role_id: int, time: int):
        await engine.execute(
            ('UPDATE roles '
             'SET time = %s '
             'WHERE guild_id = %s AND member_id = %s AND role_id = %s'),
            (time, self.guild_id, self.member_id, role_id)
        )

    @on_error()
    async def delete(self, role_id: int):
        await engine.execute(
            ('DELETE FROM roles '
             'WHERE guild_id = %s AND member_id = %s AND role_id = %s'),
            (self.guild_id, self.member_id, role_id)
        )

    @on_error()
    async def remove(self, role_id):
        _role_data = await self.get_as_role(role_id)
        if _role_data is not None:
            await self.delete(role_id)

    @on_error()
    async def set_role(self, role_id: int, time: int) -> None:
        _role_data = await self.get_as_role(role_id)
        if _role_data is None:
            await self.insert(role_id, time)
        else:
            await self.update(role_id, time)

    async def remove_role(self, member: nextcord.Member, role: nextcord.Role):
        await self.remove(role.id)
        await member.remove_roles(role)
