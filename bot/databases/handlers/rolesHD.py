from __future__ import annotations
import nextcord
from typing import Optional

from ..models import RoleModel
from ..misc.error_handler import on_error


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
        data = await RoleModel.all()
        return [(rm.guild_id, rm.member_id, rm.role_id, rm.time) for rm in data]

    @on_error()
    async def get_as_guild(self):
        data = await RoleModel.filter(guild_id=self.guild_id, system=False)
        return [(rm.member_id, rm.role_id, rm.time) for rm in data]

    @on_error()
    async def get_as_member(self):
        data = await RoleModel.filter(guild_id=self.guild_id, member_id=self.member_id, system=False)
        return [(rm.member_id, rm.role_id, rm.time) for rm in data]

    @on_error()
    async def get_as_role(self, role_id: int):
        data = await RoleModel.filter(guild_id=self.guild_id, member_id=self.member_id, role_id=role_id, system=False)
        return [rm.time for rm in data]

    @on_error()
    async def get_system(self):
        data = await RoleModel.filter(guild_id=self.guild_id, member_id=self.member_id,  system=True)
        return [(rm.member_id, rm.role_id, rm.time) for rm in data]

    @on_error()
    async def insert(self, role_id: int, time: int):
        await RoleModel.create(
            guild_id=self.guild_id,
            member_id=self.member_id,
            role_id=role_id,
            time=time
        )

    @on_error()
    async def update(self, role_id: int, time: int):
        rm = await RoleModel.get(
            guild_id=self.guild_id,
            member_id=self.member_id,
            role_id=role_id
        )
        rm.time = time
        await rm.save()

    @on_error()
    async def delete(self, role_id: int):
        rm = await RoleModel.get(
            guild_id=self.guild_id,
            member_id=self.member_id,
            role_id=role_id
        )
        await rm.delete()

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
