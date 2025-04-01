import logging
from os import getenv
import random
import string
import nextcord
from nextcord.ext import commands

from bot.databases.localdb import get_table
from bot.misc.api.types.vk_post import VkPost
from bot.misc.api.vk_api import VkApi
from bot.misc.lordbot import LordBot

_log = logging.getLogger(__name__)


class VkCallEvent(commands.Cog):
    def __init__(self, bot: LordBot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_vk_user(self, data):
        _log.trace('Access token %s', data['access_token'])

    @commands.Cog.listener()
    async def on_vk_club(self, id: int, token: str):
        _log.trace("Id %s, Token %s", id, token)

        vk = VkApi(self.bot, token)

        code = (await vk.method('groups.getCallbackConfirmationCode',
                                group_id=id))['code']
        callback_code_db = await get_table('vk_callback_code')
        await callback_code_db.set(id, code)

        server_id = (await vk.method(
            'groups.addCallbackServer',
            group_id=id,
            url=getenv('API_URL')+'/vk-callback',
            title=f"LC-{''.join([random.choice(string.ascii_lowercase) for _ in range(6)])}"
        ))['server_id']

        await vk.method(
            'groups.setCallbackSettings',
            group_id=id,
            server_id=server_id,
            wall_post_new=1
        )

    @commands.Cog.listener()
    async def on_vk_post(self, data):
        post = VkPost(data['object'])
        embeds = [
            nextcord.Embed().set_image(url)
            for url in post.attachments
        ][:5]
        await self.bot.get_channel(1210578994726969384).send(post.message,
                                                             embeds=embeds)


def setup(bot):
    bot.add_cog(VkCallEvent(bot))
