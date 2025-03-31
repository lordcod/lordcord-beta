from __future__ import annotations
import asyncio
from typing import TYPE_CHECKING
from fastapi import APIRouter, FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
import uvicorn
from bot.misc.api.vk_api_auth import VkApiAuth
from os import getenv
from fastapi.templating import Jinja2Templates

if TYPE_CHECKING:
    from bot.misc.lordbot import LordBot

SALT = '4051975f'
vk_api_auth = VkApiAuth(
    int(getenv('VK_CLIENT_ID')),
    getenv('VK_CALLBACK_URL')
)
templates = Jinja2Templates(directory="templates")


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

        config = uvicorn.Config(
            app,
            host='0.0.0.0',
            port=5000,
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
        self.app = FastAPI(debug=True)

        self.app.add_api_route(
            '/vk-callback',
            self._get_vk_callback,
            response_class=HTMLResponse
        )
        self.app.add_api_route(
            '/',
            self._get_invite,
            response_class=RedirectResponse
        )

        return self.app

    def _get_invite(self, request: Request):
        if id := request.query_params.get('group'):
            return self.vk_api_auth.get_auth_group_link(id)
        else:
            return self.vk_api_auth.get_auth_link('test')

    async def _get_vk_callback(self, request: Request):
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
            return RedirectResponse('/accept')

        for key in params.keys():
            if key.startswith('access_token_'):
                self.bot.dispatch('vk_club',
                                  int(key.removeprefix('access_token_')),
                                  params.get(key))
                return RedirectResponse('/accept')

        return templates.TemplateResponse(
            request=request,
            name="response.html",
            context={"url": '/vk-callback'}
        )


if __name__ == '__main__':
    class Bot:
        def dispatch(self, *args):
            print(args)
    VkSite(Bot()).run_sync()
