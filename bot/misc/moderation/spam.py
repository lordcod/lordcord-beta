import asyncio
import time
from typing import Dict, List, Optional, Set, Tuple

import nextcord
from .base import BaseCache
from difflib import SequenceMatcher

from bot.resources.ether import Emoji

GUILD_IDS = {1178294479267045466}
ADMINS_CATEGORY_IDS = {1178294481360003079, 1260538879757385728}
RUNNING = True


class RepeaterApi:
    @staticmethod
    def clean_symbols(word: str) -> str:
        return nextcord.utils.remove_markdown(
            word
            .replace('!', '')
            .replace('.', '')
            .replace('?', '')
            .lower()
        )

    @staticmethod
    def get_precent(a: str, b: str):
        s = SequenceMatcher(
            a=a,
            b=b
        )
        return s.ratio()

    @staticmethod
    def _is_repeat_content(a: str, b: str) -> bool:
        a = RepeaterApi.clean_symbols(a)
        b = RepeaterApi.clean_symbols(b)

        lenght = (len(a)+len(b)) / 2
        precent = RepeaterApi.get_precent(a, b)
        if not a or not b:
            return False

        if 5 > lenght:
            return a == b
        elif 10 > lenght:
            return precent > 0.78
        elif 20 > lenght:
            return precent > 0.83
        else:
            return precent > 0.93

    @staticmethod
    def _is_repeat_attach(a: List[nextcord.Attachment], b: List[nextcord.Attachment]) -> bool:
        for at1, at2 in zip(a, b):
            with_attch = at1.to_dict() == at2.to_dict()
            if not with_attch:
                return False
        return True

    @staticmethod
    def is_repeat(a: nextcord.Message, b: nextcord.Message) -> bool:
        return (
            RepeaterApi._is_repeat_content(a.content, b.content)
            and RepeaterApi._is_repeat_attach(a.attachments, b.attachments)
        )


class SpamCache(BaseCache):
    data: List[nextcord.Message]
    timeout: int
    timeout_max_time: int
    deleted_messages: Set[int]
    __spam_message: Optional[nextcord.Message] = None
    auto_delete_data: Optional[Tuple[int, str]] = None

    def __init__(self, guild_id: int, member_id: int, timeout: int = 15, timeout_max_time: int = 300) -> None:
        self.timeout = timeout
        self.timeout_max_time = timeout_max_time
        self.deleted_messages = set()

    @property
    def spam_message(self) -> Optional[nextcord.Message]:
        message = self.__spam_message
        if message is None:
            return None

        between = time.time()-message.created_at.timestamp()
        if between > 15:
            return None

        return message

    def add(self, message: nextcord.Message) -> None:
        self.data.insert(0, message)

    def get_spam_messages(self) -> List[nextcord.Message]:
        ret = set()

        for index in range(min(len(self.data)-1, 15)):
            msg1, msg2 = self.data[index:index+2]

            between = (msg1.created_at-msg2.created_at).total_seconds()
            max_time = time.time()-msg2.created_at.timestamp()

            if (
                between > self.timeout
                or max_time > self.timeout_max_time
                or not RepeaterApi.is_repeat(msg1, msg2)
            ):
                continue

            ret.add(msg1)
            ret.add(msg2)

        return list(ret)

    def is_spaming(self, message: Optional[nextcord.Message] = None, *, max_msg: int = 3) -> bool:
        messages = self.get_spam_messages()
        count = len(messages)

        if message not in messages:
            return False
        if count >= max_msg:
            self.auto_delete_data = (messages[0].created_at.timestamp(), messages[0].content)
            return True
        return False

    async def auto_delete(self, message: nextcord.Message) -> bool:
        if self.auto_delete_data is None:
            return False

        timestamp, content = self.auto_delete_data
        if (message.created_at.timestamp()-timestamp > 15
                or not RepeaterApi._is_repeat_content(message.content, content)):
            return False

        await message.delete()
        return True

    async def delete_spam_messages(self) -> nextcord.TextChannel:
        deleted = set()

        for msg in self.get_spam_messages():
            if msg.id not in self.deleted_messages:
                deleted.add(msg)
                self.deleted_messages.add(msg)

        tasks: Dict[nextcord.TextChannel, List[nextcord.Message]] = {}
        compiled = []

        for msg in list(deleted):
            tasks.setdefault(msg.channel, [])
            tasks[msg.channel].append(msg)

        for chnl, msgs in tasks.items():
            compiled.append(chnl.delete_messages(msgs))

        await asyncio.gather(*compiled)

        return list(tasks.keys())[0]

    async def send_spam_message(self, channel: nextcord.TextChannel) -> None:
        message = await channel.send(f'{Emoji.cross} <@{self.member_id}> Прекратите рассылать спам',
                                     delete_after=15)
        self.__spam_message = message


async def parse_message(message: nextcord.Message):
    return

    if message.author.bot:
        return

    if not RUNNING:
        return

    if message.guild is None or message.guild.id not in GUILD_IDS:
        return

    category_id = message.channel.category_id
    if category_id in ADMINS_CATEGORY_IDS:
        return

    cache = SpamCache(message.guild.id, message.author.id)
    cache.add(message)

    if await cache.auto_delete(message):
        if cache.spam_message is None:
            await cache.send_spam_message(message.channel)
        return

    if cache.is_spaming(message):
        chnl = await cache.delete_spam_messages()
        if cache.spam_message is None:
            await cache.send_spam_message(chnl)
