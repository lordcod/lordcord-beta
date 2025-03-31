from __future__ import annotations
import asyncio
from typing import TYPE_CHECKING
from fastapi import APIRouter, FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
import uvicorn
from bot.misc.api.vk_api_auth import VkApiAuth

if TYPE_CHECKING:
    from bot.misc.lordbot import LordBot

SALT = '4051975f'
app = FastAPI()
vk_api_auth = VkApiAuth(
    51922313,
    'https://lordcord.xyz/vk-callback'
)


class VkSite:
    def __init__(self, bot: LordBot) -> None:
        self.bot = bot
        self.vk_api_auth = vk_api_auth
        self.__running = False

    def is_running(self) -> bool:
        return self.__running

    async def run(self,
                  *,
                  port: int = 8000) -> None:
        if self.__running:
            return

        self.__running = True
        app = self._setup()

        config = uvicorn.Config(app, host='0.0.0.0',
                                port=5000, log_level="info",
                                log_config={'version': 1})
        server = uvicorn.Server(config)
        await server.serve()

    def run_sync(self):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.run())

    def _setup(self):
        self.app = FastAPI(debug=True)
        for router in self._get_routers():
            self.app.include_router(router)
        return self.app

    def _get_routers(self) -> APIRouter:
        routers = []

        router = APIRouter()
        router.add_api_route(
            '/', self._get, methods=["HEAD", "GET"], status_code=204)
        routers.append(router)
        return routers

    async def _get(self, request: Request):
        params = request.query_params

        if vk_api_auth.session is None:
            vk_api_auth.session = self.bot.session

        if not set(['code', 'state', 'device_id']) - set(params.keys()):
            data = await vk_api_auth.verifi(params.get('state'),
                                            params.get('device_id'),
                                            params.get('code'))

            if 'error' in data:
                return data['error_description']

            self.bot.dispatch('vk_user', data)
            return RedirectResponse('/')

        for key in params.keys():
            if key.startswith('access_token_'):
                self.bot.dispatch('vk_club',
                                  int(key.removeprefix('access_token_')),
                                  params.get(key))
                return RedirectResponse('/')

        return HTMLResponse(open('assets/vksite_response.html', 'rb').read())


if __name__ == '__main__':
    class Bot:
        def dispatch(self, *args):
            print(args)
    VkSite(Bot()).run_sync()
