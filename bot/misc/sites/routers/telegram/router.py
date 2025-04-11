from __future__ import annotations

import asyncio
from functools import partial
import logging
from os import getenv
from typing import TYPE_CHECKING
import random

from pathlib import Path
from base64 import urlsafe_b64encode
from string import printable
from fastapi import APIRouter, Request, Response

from aiogram.types import Update


from .bot import dp

if TYPE_CHECKING:
    from bot.misc.lordbot import LordBot

_log = logging.getLogger(__name__)
token = urlsafe_b64encode(
    ''.join([random.choice(printable)
             for _ in range(24)]).encode()).decode()


class TelegramRouter:
    def __init__(self, bot: LordBot):
        self.bot = bot
        self.tg_bot = bot.telegram_client
        self.callback_url = None

    def _setup(self, prefix: str = ''):
        dp['dispatch'] = self.bot.dispatch
        self.callback_url = getenv('API_URL')+prefix+'/'

        router = APIRouter(
            prefix=prefix,
            on_startup=[lambda: asyncio.create_task(self.on_startup())]
        )

        router.add_api_route('/', self._get, methods=['GET'])
        router.add_api_route('/icon/{id}', self._get_icon, methods=['GET'])
        router.add_api_route('/', self._post, methods=['POST'])

        return router

    async def on_startup(self):
        _log.trace('Registered tg webhook as %s', self.callback_url)
        await self.tg_bot.set_webhook(self.callback_url,
                                      allowed_updates=dp.resolve_used_update_types(),
                                      secret_token=token,
                                      drop_pending_updates=True)

    async def _get_icon(self, request: Request, id: int):
        chat = await self.tg_bot.get_chat(id)
        if chat.photo is None:
            return Response(status_code=204)
        file = await self.tg_bot.get_file(chat.photo.big_file_id)
        io = await self.tg_bot.download_file(file.file_path)
        return Response(content=io.read(), media_type="image/"+Path(file.file_path).suffix.removeprefix('.'))

    async def _get(self, request: Request):
        return await self.tg_bot.get_webhook_info()

    async def _post(self, request: Request):
        secret = request.headers.get('X-Telegram-Bot-Api-Secret-Token')
        if secret != token:
            return Response(status_code=401)

        data = await request.json()
        update = Update.model_validate(data, context={"bot": self.tg_bot})
        await dp.feed_update(self.tg_bot, update)
