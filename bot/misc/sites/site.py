from __future__ import annotations

import asyncio
import os
from typing import TYPE_CHECKING
from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from bot.misc.sites.routers.command import CommandRouter
from bot.misc.sites.routers.telegram.router import TelegramRouter
from bot.misc.sites.routers.websokets import WebSocketRouter
from .routers.database import DataBaseRouter
from .routers.vk import VkRouter

if TYPE_CHECKING:
    from bot.misc.lordbot import LordBot


class ApiSite:
    def __init__(self, bot: LordBot) -> None:
        self.bot = bot
        self.app = FastAPI()

        origins = [
            "http://localhost.tiangolo.com",
            "https://localhost.tiangolo.com",
            "http://localhost",
            "http://localhost:8080",
            "http://localhost:5173",
        ]

        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        self.__running = False

    def is_running(self) -> bool:
        return self.__running

    async def run(self,
                  *,
                  port: int = 5000) -> None:
        if self.__running:
            return

        self.__running = True

        router = self._setup()
        self.app.include_router(router)

        config = uvicorn.Config(
            self.app,
            host='0.0.0.0',
            port=port,
            log_level=None,
            access_log=None,
            log_config=None,
        )

        if os.path.exists('keys/cert.pem') and os.path.exists('keys/key.pem') and False:
            config.ssl_certfile = 'keys/cert.pem'
            config.ssl_keyfile = 'keys/key.pem'

        server = uvicorn.Server(config)
        await server.serve()

    def run_sync(self):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.run())

    def _setup(self) -> APIRouter:
        router = APIRouter()

        router.add_api_route('/accept', self._get_accept)
        router.include_router(WebSocketRouter(self.bot)._setup())
        router.include_router(VkRouter(self.bot)._setup('/vk'))
        router.include_router(DataBaseRouter(self.bot)._setup('/database'))
        router.include_router(CommandRouter(self.bot)._setup('/commands'))
        router.include_router(TelegramRouter(self.bot)._setup('/telegram'))

        return router

    async def _get_accept(self):
        return {'status': 'ok'}
