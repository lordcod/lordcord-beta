from __future__ import annotations
import base64
import hashlib
from typing import TYPE_CHECKING, Optional
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse
from bot.misc.api.vk_api_auth import VkApiAuth
from os import getenv
from fastapi.templating import Jinja2Templates

if TYPE_CHECKING:
    from bot.misc.lordbot import LordBot

SALT = '4051975f'
password = hashlib.sha256("random string".encode()).digest()
templates = Jinja2Templates(directory="templates")


def decrypt(enc_data: str) -> str:
    enc_bytes = base64.urlsafe_b64decode(enc_data)
    return "".join(chr(a ^ b) for a, b in zip(enc_bytes, password))


class VkRouter:
    def __init__(
        self,
        bot: LordBot,
        client_id: int = int(getenv('VK_CLIENT_ID')),
        redirect_uri: Optional[str] = None
    ) -> None:
        self.bot = bot
        self.vk_api_auth = VkApiAuth(
            client_id,
            redirect_uri
        )

    def _setup(self, prefix: str = "") -> APIRouter:
        if self.vk_api_auth.redirect_uri is None:
            self.vk_api_auth.redirect_uri = getenv(
                'API_URL', '')+prefix+'/callback'

        router = APIRouter(prefix=prefix)

        router.add_api_route(
            '/callback',
            self._get_vk_callback,
            methods=['GET'],
            response_class=HTMLResponse
        )
        router.add_api_route(
            '/callback/{code}',
            self._post_vk_callback,
            methods=['POST'],
            response_class=PlainTextResponse
        )
        router.add_api_route(
            '/invite',
            self._get_invite,
            response_class=RedirectResponse
        )

        return router

    async def _post_vk_callback(self, request: Request, code: str):
        data = await request.json()

        enc = decrypt(code)
        randhex, group_id, group_code = enc.split('-')

        if data['type'] == 'confirmation':
            return group_code

        self.bot.dispatch('vk_post', data)

        return 'ok'

    async def _get_invite(self, request: Request, state: str,  group: Optional[int] = None):
        if group is not None:
            return self.vk_api_auth.get_auth_group_link(group, state)
        return self.vk_api_auth.get_auth_link(state)

    async def _get_vk_callback(self, request: Request):
        params = request.query_params

        if self.vk_api_auth.session is None:
            self.vk_api_auth.session = self.bot.session

        if not set(['code', 'state', 'device_id']) - set(params.keys()):
            data = await self.vk_api_auth.verifi(params.get('state'),
                                                 params.get('device_id'),
                                                 params.get('code'))

            if 'error' in data:
                return data['error_description']

            self.bot.dispatch('vk_user', data)
            return RedirectResponse('/accept')

        for key in params.keys():
            if key.startswith('access_token_'):
                self.bot.dispatch(
                    'vk_club',
                    int(key.removeprefix('access_token_')),
                    params.get(key),
                    params.get('state')
                )
                return RedirectResponse('/accept')

        return templates.TemplateResponse(
            request=request,
            name="response.html",
            context={"url": self.vk_api_auth.redirect_uri}
        )
