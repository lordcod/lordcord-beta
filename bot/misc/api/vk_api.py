from __future__ import annotations
from typing import TYPE_CHECKING, cast


if TYPE_CHECKING:
    from bot.misc.lordbot import LordBot


class VkApiError(Exception):
    def __init__(self, method, error):
        super(Exception, self).__init__()
        self.method = method
        self.code = error['error_code']
        self.error = error

    def __str__(self):
        return '[{}] {}'.format(self.error['error_code'],
                                self.error['error_msg'])


class VkApi:
    def __init__(self, bot: LordBot, token: str, version: int = 5.131):
        self.bot = bot
        self.token = token
        self.base_url = 'https://api.vk.com/method/'
        self.version = version

    async def method(self, method_name: str, values: dict = None, **kwargs):
        if not isinstance(method_name, str):
            raise TypeError(
                'The %s type does not match the str parameter'
                % type(method_name).__name__)
        if values is not None and not isinstance(method_name, dict):
            raise TypeError(
                'The %s type does not match the dict parameter'
                % type(method_name).__name__)

        base_url = self.base_url + method_name

        if values is None:
            values = {}
        values.update(kwargs)
        values.update({'access_token': self.token, 'v': self.version})

        async with self.bot.session.post(base_url, data=values) as resp:
            response = cast(dict, await resp.json())

            if 'error' in response.keys():
                error = VkApiError(method_name, {
                    'error_msg': response, 'error_code': response["error"]["error_code"]})
                raise error

            return response['response']
