import base64
import hashlib
import uuid
from nextcord.ext import commands
import logging
from os import getenv
import random
import string

from bot.misc.lordbot import LordBot
from bot.misc.api.vk_api import VkApi, VkApiError

_log = logging.getLogger(__name__)

password = hashlib.sha256("random string".encode()).digest()


def encrypt(data: str) -> str:
    enc_bytes = bytes(a ^ b for a, b in zip(
        data.encode(), password))
    return base64.urlsafe_b64encode(enc_bytes).decode()


class VkCallEvent(commands.Cog):
    def __init__(self, bot: LordBot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_vk_user(self, data):
        vk = VkApi(self.bot, data['access_token'])
        response = await vk.method(
            'groups.get',
            filter='admin',
            extended=1
        )
        answer = {
            'method': 'groups.get',
            'response': response
        }
        await self.bot.send_api_state(data['state'], answer)

    @commands.Cog.listener()
    async def on_vk_club(self, id: int, token: str, state: str):
        vk = VkApi(self.bot, token)

        code = (await vk.method('groups.getCallbackConfirmationCode',
                                group_id=id))['code']
        enc = encrypt(f"{uuid.uuid4().int % 1_000_000}-{id}-{code}")

        try:
            server_id = (await vk.method(
                'groups.addCallbackServer',
                group_id=id,
                url=getenv('API_URL')+'/vk/callback/'+enc,
                title=f"LC-{''.join([random.choice(string.ascii_lowercase) for _ in range(6)])}"
            ))['server_id']
        except VkApiError as exc:
            await self.bot.send_api_state(state,
                                          {'method': 'error',
                                           'message': exc.error['error_msg']})
            return

        await vk.method(
            'groups.setCallbackSettings',
            group_id=id,
            server_id=server_id,
            wall_post_new=1
        )

        await self.bot.send_api_state(state,
                                      {'method': 'groups.addCallbackServer',
                                       'status': 'ok'})


def setup(bot):
    bot.add_cog(VkCallEvent(bot))
