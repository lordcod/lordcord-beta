from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING
from fastapi import APIRouter, FastAPI
import uvicorn

from bot.misc.sites.routers.command import CommandRouter
from .routers.database import DataBaseRouter
from .routers.vk import VkRouter

if TYPE_CHECKING:
    from bot.misc.lordbot import LordBot


class ApiSite:
    def __init__(self, bot: LordBot) -> None:
        self.bot = bot
        self.app = FastAPI()
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
        server = uvicorn.Server(config)
        await server.serve()

    def run_sync(self):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.run())

    def _setup(self) -> APIRouter:
        router = APIRouter()

        router.include_router(VkRouter(self.bot)._setup('/vk'))
        router.include_router(DataBaseRouter(self.bot)._setup('/database'))
        router.include_router(CommandRouter(self.bot)._setup('/commands'))

        return router
