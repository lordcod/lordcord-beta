from __future__ import annotations
from typing import TYPE_CHECKING
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
import jwt
from bot.databases.handlers.guildHD import GuildDateBases
if TYPE_CHECKING:
    from bot.misc.lordbot import LordBot

SALT = '4051975f'
SALT = '6F530A9BE83CA1CE0F957A985A662A5AEDDEC2B2B24BD9C91AFC7163C40F1848'
templates = Jinja2Templates(directory="templates")


permission = {
    'admin': 10,
    'database': 8
}


def check_scope(scope: str, required: str) -> bool:
    return (
        scope == required
        or (required in permission
            and permission.get(scope, 0) > permission[required])
    )


def check_scopes(scope: str, requires: list[str]):
    return any(check_scope(scope, r) for r in requires)


class Tokenizer:
    @staticmethod
    def generate_token(payload: dict):
        return jwt.encode(payload, SALT, algorithm="HS256")

    @staticmethod
    def get_payload(token: str | Request):
        if isinstance(token, Request):
            token = token.headers.get('Authorization')
        return jwt.decode(token, SALT, algorithms="HS256")


class DataBaseRouter:
    def __init__(
        self,
        bot: LordBot
    ) -> None:
        self.bot = bot

    def _setup(self, prefix: str = "") -> APIRouter:
        router = APIRouter(prefix=prefix)

        router.add_api_route(
            '/',
            self._put,
            methods=['PUT'],
            status_code=204
        )
        router.add_api_route(
            '/',
            self._get,
            methods=['GET']
        )

        return router

    async def _get(self, request: Request, key: str):
        payload = Tokenizer.get_payload(request)
        status = check_scopes(
            payload['scope'],
            ['database', 'database.'+key]
        )
        if not status:
            return JSONResponse({
                'error': 'Not authorization'
            }, status_code=401)

        gdb = GuildDateBases(int(payload['guild_id']))
        return await gdb.get(key)

    async def _put(self, request: Request):
        data = await request.json()
        payload = Tokenizer.get_payload(request)

        status = check_scopes(
            payload['scope'],
            ['database', 'database.'+data['key']]
        )
        if not status:
            return JSONResponse({
                'error': 'Not authorization'
            }, status_code=401)

        gdb = GuildDateBases(int(payload['guild_id']))
        await gdb.set(data['key'], data['value'])
