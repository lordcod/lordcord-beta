from __future__ import annotations
from typing import Optional, TypeVar, overload
from ..models import GuildModel

T = TypeVar('T')


class CommandDB:
    def __init__(self, guild_id: int) -> None:
        self.guild_id = guild_id

    @overload
    async def get(self, command: str) -> Optional[dict]: ...

    @overload
    async def get(self, command: str, default: T) -> T: ...

    async def get(self, command: str, default: T = None) -> dict | T:
        gm = await GuildModel.get(id=self.guild_id)
        data = gm.command_permissions
        if not data:
            return default
        return data.get(command, default)

    async def update(self, key: str, value: dict) -> None:
        gm = await GuildModel.get(id=self.guild_id)
        gm.command_permissions[key] = value
        gm.save()
