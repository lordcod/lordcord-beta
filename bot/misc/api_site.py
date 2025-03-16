from __future__ import annotations

import logging
import random
import string
import time
from typing import TYPE_CHECKING, Dict
from aiohttp import ContentTypeError
import orjson
import asyncio
from uvicorn import Config, Server
from pyngrok import ngrok, conf
from fastapi import FastAPI, APIRouter, Request, Response


if TYPE_CHECKING:
    from bot.misc.lordbot import LordBot


_log = logging.getLogger(__name__)
pyngrok_config = conf.PyngrokConfig(log_event_callback=lambda log: None,
                                    max_logs=10)


class ApiSite:
    endpoint: str
    password: str
    callback_url: str
    app: FastAPI
    __running: bool = False

    def __init__(self,
                 bot: LordBot,
                 handlers: list) -> None:
        self.bot = bot
        self.handlers = handlers
        self._cache: Dict[str, int] = {}

    async def on_ready(self):
        _log.info('ApiSite is ready, public url: %s, password: %s', self.callback_url, self.password)

    def is_running(self) -> bool:
        return self.__running

    async def __run(self,
                    *,
                    endpoint: str = '/',
                    port: int = 8000) -> None:
        if self.__running:
            return

        self.__running = True
        server = self._setup(endpoint=endpoint, port=port)
        try:
            server.config.setup_event_loop()
            await server.serve()
        except KeyboardInterrupt:
            await server.shutdown()

    def run(self):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.__run())

    def _setup(self, endpoint: str, port: int):
        self.endpoint = endpoint
        self.password = ''.join([random.choice(string.hexdigits) for _ in range(25)])
        self.callback_url = ngrok.connect(str(port), pyngrok_config=pyngrok_config).public_url

        self.app = FastAPI(debug=True)
        for router in self._get_routers():
            self.app.include_router(router)
        self.app.add_event_handler("startup", lambda: asyncio.create_task(self.on_ready()))

        config = Config(self.app, "0.0.0.0", port, log_config=None, log_level=logging.CRITICAL)
        server = Server(config)
        return server

    def _get_routers(self) -> APIRouter:
        routers = []

        router = APIRouter()
        router.add_api_route(self.endpoint, self._get, methods=["HEAD", "GET"])
        router.add_api_route(self.endpoint, self._post, methods=["POST"])
        routers.append(router)

        router = APIRouter()
        router.add_api_route(self.endpoint+'update/', self._post_update, methods=["POST"])
        routers.append(router)

        return routers

    async def _post_update(self, request: Request):
        result = await self.bot.update_api_config()
        if result:
            return Response(status_code=204)
        else:
            return Response(status_code=500)

    async def _get(self, request: Request):
        return Response(status_code=204)

    async def _post(self, request: Request):
        if not self._is_authorization(request):
            return Response(status_code=401)

        try:
            json = await request.json()

            endpoint = json['endpoint']
            data = json['data']

            func = self.handlers[endpoint]
        except ContentTypeError:
            return Response(status_code=400)
        except KeyError:
            return Response(status_code=400)
        else:
            limit = func.__limit__

            if limit is not None and self._cache.get(endpoint, 0)+limit > time.time():
                return Response(
                    status_code=429,
                    headers={
                        'X-After-Request': str(self._cache.get(endpoint, 0)+limit-time.time())
                    }
                )

            self._cache[endpoint] = time.time()
            result = await func(self.bot, data)
            return Response(
                orjson.dumps(result),
                headers={
                    'Content-Type': 'application/json'
                }
            )

    def _is_authorization(self, request: Request) -> bool:
        password = request.headers.get('Authorization')
        return self.password == password


if __name__ == '__main__':
    api = ApiSite('Any', [])
    api.run()
