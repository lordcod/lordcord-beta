import contextlib
import re
from pathlib import Path
from typing import Optional
from nextcord import File
import nextcord
from nextcord.ext import commands
import logging
from bot.databases.datastore import DataStore
from bot.databases.models import GuildModel, Q
from bot.misc.env import API_URL
from bot.misc.lordbot import LordBot
from aiogram.types import Message
from aiogram.enums import MessageEntityType
from aiogram.utils.text_decorations import MarkdownDecoration

_log = logging.getLogger(__name__)


class DiscordMarkdownDecoration(MarkdownDecoration):
    MARKDOWN_QUOTE_PATTERN = re.compile(r"([_*\[\]()~`>#+\-=|\\])")

    def apply_entity(self, entity, text):
        if entity.type == MessageEntityType.TEXT_MENTION:
            return self.link(value=text, link=f"https://t.me/{entity.user.username}")
        return super().apply_entity(entity, text)

    def custom_emoji(self, value: str, custom_emoji_id: str) -> str:
        return value

    def blockquote(self, value: str) -> str:
        return "\n".join(f"> {line}" for line in value.splitlines())

    def expandable_blockquote(self, value: str) -> str:
        return self.blockquote(value)


discord_decoration = DiscordMarkdownDecoration()


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


class TgCallEvent(commands.Cog):
    def __init__(self, bot: LordBot):
        self.bot = bot

    async def get_channels(self, id: int):
        channels = []
        guilds = await GuildModel.filter(~Q(telegram_notification={}))
        for gm in guilds:
            for data in gm.telegram_notification.values():
                if data['chat_id'] == id and (
                        chnl := self.bot.get_channel(data['channel_id'])):
                    channels.append([chnl, data])
        return channels

    @commands.Cog.listener()
    async def on_tg_post(self, message: Message):
        if message.message_id in updates:
            return
        updates.append(message.message_id)

        _log.trace('Receive callback data (id:%s): %s',
                   message.message_id, message.text)

        try:
            topic = message.reply_to_message.forum_topic_created.name
        except AttributeError:
            topic = None

        embeds = []
        files = []

        if message.document:
            file = await message.bot.get_file(message.document.file_id)
            io = await message.bot.download_file(file.file_path)
            files.append(File(io, message.document.file_name))

        if message.photo:
            file = await message.bot.get_file(message.photo[-1].file_id)
            io = await message.bot.download_file(file.file_path)

            filename = f"{id}.{Path(file.file_path).suffix}"
            files.append(
                File(io, filename=filename))
            embeds.append(nextcord.Embed(description='').set_image(
                f"attachment://{filename}"))

        content = message._unparse_entities(discord_decoration)
        avatar_url = f'{API_URL}/telegram/icon/{message.chat.id}'

        channels = await self.get_channels(message.chat.id)
        for channel, data in channels:
            categories = data.get('categories', [])
            if categories is not None and topic not in categories:
                continue

            webhook = await get_webhook(channel)
            await webhook.send(content,
                               username=message.chat.title,
                               avatar_url=avatar_url,
                               embeds=embeds,
                               files=files)


def setup(bot):
    bot.add_cog(TgCallEvent(bot))
