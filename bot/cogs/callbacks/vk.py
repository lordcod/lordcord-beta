import base64
import contextlib
import random
import string
from typing import Optional
import uuid
import nextcord
from nextcord.ext import commands
import logging

from bot.databases.datastore import DataStore
from bot.databases.models import GuildModel, Q
from bot.misc.env import API_URL
from bot.misc.lordbot import LordBot
from bot.misc.api.vk_api import VkApi, VkApiError
from bot.misc.utils.misc import Tokenizer

_log = logging.getLogger(__name__)

HASH = "RUkFEDT2pGQnnEbF"
password = Tokenizer.generate_key(HASH)


def encrypt(data: str) -> str:
    enc_bytes = bytes(a ^ b for a, b in zip(
        data.encode(), password))
    return base64.urlsafe_b64encode(enc_bytes).decode()


async def get_webhook(channel: nextcord.TextChannel) -> Optional[nextcord.Webhook]:
    client = channel._state._get_client()
    webhooks_db = DataStore('notification_webhooks')
    webhook_data = await webhooks_db.get(channel.id)

    if webhook_data is not None:
        webhook_data['type'] = 1
        cache_webhook = nextcord.Webhook.from_state(
            webhook_data, channel._state)

        with contextlib.suppress(nextcord.NotFound):
            webhook = await cache_webhook.fetch(prefer_auth=False)
            if webhook.channel_id == channel.id:
                return webhook

    if not channel.permissions_for(channel.guild.me).manage_webhooks:
        return None

    webhook = await channel.create_webhook(
        name=f'{client.user.name} Notification',
        avatar=client.user.avatar
    )
    await webhooks_db.set(channel.id, {'id': webhook.id, 'token': webhook.token})

    return webhook

updates = []


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
        enc = Tokenizer.encrypt(f"{uuid.uuid4().int % 1_000_000}-{id}-{code}",
                                password)

        try:
            server_id = (await vk.method(
                'groups.addCallbackServer',
                group_id=id,
                url=API_URL+'/vk/callback/'+enc,
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

        vk_tokens_db = DataStore('vk_tokens')
        await vk_tokens_db.set(id, token)

        await self.bot.send_api_state(state,
                                      {'method': 'groups.addCallbackServer',
                                       'status': 'ok'})

    async def get_channels(self, id: int):
        channels = set()
        guilds = await GuildModel.filter(~Q(vk_notification={}))
        for gm in guilds:
            for data in gm.vk_notification.values():
                if data['group_id'] == id and (
                        chnl := self.bot.get_channel(data['channel_id'])):
                    channels.add(chnl)
        return channels

    @commands.Cog.listener()
    async def on_vk_post(self, data: dict):
        post_id = data["object"]["id"]
        if post_id in updates:
            return
        updates.append(post_id)

        _log.trace('Receive VK post (id:%s): %s',
                   post_id, data["object"].get("text", ""))

        group_id = data["group_id"]
        vk_tokens_db = DataStore('vk_tokens')
        token = await vk_tokens_db.get(group_id)
        if token:
            vk = VkApi(self.bot, token)
            response = await vk.method('groups.getById',
                                       group_id=group_id)
            group = response[0]
            group_name = group["name"]
            avatar_url = group["photo_200"]
        else:
            group_name = 'Vk Group'
            avatar_url = None

        embeds = []
        files = []

        text = data["object"].get("text", "")

        attachments = data["object"].get("attachments", [])
        for attachment in attachments:
            if attachment["type"] == "photo":
                sizes = attachment["photo"]["sizes"]
                photo_url = sorted(sizes, key=lambda x: x["width"])[-1]["url"]
                embeds.append(
                    nextcord.Embed(description='').set_image(url=photo_url)
                )
            elif attachment["type"] == "doc":
                doc = attachment["doc"]
                file_url = doc["url"]
                filename = doc["title"]

                embeds.append(
                    nextcord.Embed(title=filename, url=file_url,
                                   description="Документ VK")
                )

        channels = await self.get_channels(group_id)
        for channel in channels:
            webhook = await get_webhook(channel)

            await webhook.send(
                text or None,
                username=group_name,
                avatar_url=avatar_url,
                embeds=embeds,
                files=files
            )


def setup(bot):
    bot.add_cog(VkCallEvent(bot))
