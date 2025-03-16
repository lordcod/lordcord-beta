from __future__ import annotations
from typing import Optional, TypeVar, overload
from ..db_engine import DataBase

T = TypeVar('T')
engine: DataBase = None


class CommandDB:
    def __init__(self, guild_id: int) -> None:
        self.guild_id = guild_id

    @overload
    async def get(self, command: str) -> Optional[dict]: ...

    @overload
    async def get(self, command: str, default: T) -> T: ...

    async def get(self, command: str, default: T = None) -> dict | T:
        data = await engine.fetchvalue(
            "SELECT command_permissions FROM guilds WHERE id = %s",
            (self.guild_id,)
        )
        if data is None:
            return default
        return data.get(command, default)

    async def update(self, key: str, value: dict) -> None:
        data = await engine.fetchvalue(
            "SELECT command_permissions FROM guilds WHERE id = %s",
            (self.guild_id,)
        )
        data[key] = value
        await engine.execute(
            """
                UPDATE guilds 
                SET command_permissions = %s
                WHERE id = %s
            """,
            (data, self.guild_id, )
        )
