from __future__ import annotations
from typing import TYPE_CHECKING, Optional
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
import jwt
from bot.databases.handlers.guildHD import GuildDateBases
if TYPE_CHECKING:
    from bot.misc.lordbot import LordBot

SALT = '6F530A9BE83CA1CE0F957A985A662A5AEDDEC2B2B24BD9C91AFC7163C40F1848'
templates = Jinja2Templates(directory="templates")


class Tokenizer:
    @staticmethod
    def generate_token(payload: dict):
        return jwt.encode(payload, SALT, algorithm="HS256")

    @staticmethod
    def get_payload(token: str | Request) -> dict:
        if isinstance(token, Request):
            token = token.headers.get('Authorization')
        return jwt.decode(token, SALT, algorithms="HS256")

def check_permission(payload, guild_id, key):
    if (
        payload['scope'] not in ['admin', 'database', 'database.'+key]
        or ('guild_id' not in payload and payload['scope'] != 'admin')
        or ((pgid := payload.get('guild_id')) and int(pgid) != guild_id)
    ):
        return JSONResponse({
            'error': 'Not authorization'
        }, status_code=401)


class DataBaseRouter:
    def __init__(
        self,
        bot: LordBot
    ) -> None:
        self.bot = bot

    def _setup(self, prefix: str = "") -> APIRouter:
        router = APIRouter(prefix=prefix)

        router.add_api_route(
            '/{guild_id}/{key}/',
            self._put,
            methods=['PUT'],
            status_code=204
        )
        router.add_api_route(
            '/{guild_id}/{key}/',
            self._get,
            methods=['GET']
        )

        return router

    async def _get(self, request: Request, guild_id: int, key: str):
        payload = Tokenizer.get_payload(request)
        if response := check_permission(payload, guild_id, key):
            return response

        print(key)
        gdb = GuildDateBases(guild_id)
        return await gdb.get(key)

    async def _put(self, request: Request, guild_id: int, key: str):
        data = await request.json()
        payload = Tokenizer.get_payload(request)
        if response := check_permission(payload, guild_id, key):
            return response

        if not guild_id:
            raise Exception('Guild id is none')

        gdb = GuildDateBases(guild_id)
        await gdb.set(key, data)
