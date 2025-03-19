from __future__ import annotations
from typing import Optional
import nextcord
from nextcord.state import ConnectionState

from ..models import BanModel


class BanDateBases:
    def __init__(
        self,
        guild_id: Optional[int] = None,
        member_id: Optional[int] = None
    ) -> None:
        self.guild_id = guild_id
        self.member_id = member_id

    async def get_all(self):
        data = await BanModel.all()
        return [(bm.guild_id, bm.member_id, bm.time) for bm in data]

    async def get_as_guild(self):
        data = await BanModel.filter(guild_id=self.guild_id)
        return [(bm.member_id, bm.time) for bm in data]

    async def get_as_member(self):
        data = await BanModel.filter(guild_id=self.guild_id,
                                     member_id=self.member_id)
        return [bm.time for bm in data]

    async def insert(self, time: int):
        await BanModel.create(guild_id=self.guild_id,
                              member_id=self.member_id,
                              time=time)

    async def update(self, new_time: int):
        bm = await BanModel.get(guild_id=self.guild_id,
                                member_id=self.member_id)
        bm.time = new_time
        await bm.save()

    async def delete(self):
        bm = await BanModel.get(guild_id=self.guild_id,
                                member_id=self.member_id)
        await bm.delete()

    async def remove_ban(self, _state: ConnectionState, reason: Optional[str] = None):
        await self.delete()
        try:
            await _state.http.unban(self.member_id,
                                    self.guild_id,
                                    reason=reason)
        except nextcord.NotFound:
            pass
