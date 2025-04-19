import asyncio
import functools
import random
import time
import nextcord
import math
from nextcord.ext import commands

from bot.databases import GuildDateBases
from bot.databases.datastore import DataStore
from bot.misc.plugins import logstool
from bot.misc.lordbot import LordBot
from bot.misc.moderation.spam import parse_message
from bot.misc.plugins.tickettools import ModuleTicket
from bot.misc.utils import is_emoji
from bot.languages import i18n
from bot.views.translate import AutoTranslateView

import googletrans

translator = googletrans.Translator()

BETWEEN_MESSAGES_TIME = {}
LAST_MESSAGES_USER = {}


_pat_current_delay = {}


def disable(func):
    @functools.wraps(func)
    async def wrapped(*args, **kwargs):
        return None
    return wrapped


def create_delay_at_pat(delay: float):
    def _create_delay_at(func):
        @functools.wraps(func)
        async def wrapped(self, message: nextcord.Message):
            if _pat_current_delay.get(message.guild.id, 0) > time.time():
                return
            _pat_current_delay[message.guild.id] = time.time()+delay
            return await func(self, message)
        return wrapped
    return _create_delay_at


class MessageEvent(commands.Cog):
    def __init__(self, bot: LordBot) -> None:
        self.bot = bot
        self.bot
        super().__init__()

    @commands.Cog.listener()
    async def on_message(self, message: nextcord.Message):
        if message.guild is None:
            return
        await asyncio.gather(
            ModuleTicket.archive_message(message),
            self.add_reactions(message),
            self.process_mention(message),
            self.give_score(message),
            self.give_message_score(message),
            self.process_auto_translation(message),
            parse_message(message)
        )

    @create_delay_at_pat(15)
    @disable
    async def process_auto_translation(self, message: nextcord.Message) -> None:
        gdb = GuildDateBases(message.guild.id)
        auto_translation = await gdb.get('auto_translate')

        if not (message.channel.id in auto_translation
                and message.content) or message.author.bot:
            return

        webhooks = await message.channel.webhooks()
        for wh in webhooks:
            if wh.user != self.bot.user:
                bot_wh = wh
                break
        else:
            bot_wh = await message.channel.create_webhook(name=self.bot.user.display_name,
                                                          avatar=self.bot.user.display_avatar)

        view = AutoTranslateView()
        files = await asyncio.gather(*[attach.to_file(use_cached=True, spoiler=attach.is_spoiler()
                                                      ) for attach in message.attachments]
                                     ) if message.attachments else None
        await asyncio.gather(
            bot_wh.send(
                content=message.content,
                files=files,
                view=view,
                username=message.author.display_name,
                avatar_url=message.author.display_avatar.url
            ),
            message.delete()
        )

    async def add_reactions(self, message: nextcord.Message) -> None:
        gdb = GuildDateBases(message.guild.id)

        if (reactions := await gdb.get('reactions', {})) and (
                data_reactions := reactions.get(message.channel.id)):
            for reat in data_reactions:
                if not is_emoji(reat):
                    continue
                asyncio.create_task(message.add_reaction(
                    reat), name=f'auto-reaction:{message.guild.id}:{message.channel.id}:{message.id}')

    async def process_mention(self, message: nextcord.Message) -> None:
        gdb = GuildDateBases(message.guild.id)

        color = await gdb.get('color')
        locale = await gdb.get('language')
        prefix = await gdb.get('prefix')

        if message.content.strip() == self.bot.user.mention:
            embed = nextcord.Embed(
                title=i18n.t(locale, 'bot-info.title',
                             name=self.bot.user.display_name),
                description=i18n.t(
                    locale, 'bot-info.description', prefix=prefix),
                color=color
            )
            embed.add_field(name='Assembly Information', value=i18n.t(
                locale, 'bot-info.assembly', version=self.bot.release_tag,
                hash=self.bot.release_sha, time=self.bot.release_date))

            asyncio.create_task(message.channel.send(embed=embed))

    async def give_message_score(self, message: nextcord.Message) -> None:
        gdb = GuildDateBases(message.guild.id)
        guild_state = await gdb.get('message_state', {})
        guild_state[message.author.id] = guild_state.get(
            message.author.id, 0) + 1
        await gdb.set('message_state', guild_state)

        state = DataStore('messages')
        await state.increment(message.author.id)

    async def give_score(self, message: nextcord.Message) -> None:
        if message.author.bot:
            return
        lmu = LAST_MESSAGES_USER.get(
            f"{message.guild.id}:{message.channel.id}")
        LAST_MESSAGES_USER[f"{message.guild.id}:{message.channel.id}"] = message.author.id
        if lmu == message.author.id and BETWEEN_MESSAGES_TIME.get(message.author.id, 0) > time.time():
            return

        multiplier = 1
        user_level = 1
        score = random.randint(
            0, 10) * multiplier / math.sqrt(user_level)

        gdb = GuildDateBases(message.guild.id)
        guild_state = await gdb.get('score_state', {})
        guild_state[message.author.id] = guild_state.get(
            message.author.id, 0) + score
        await gdb.set('score_state', guild_state)

        state = DataStore('score')
        await state.increment(message.author.id, score)

        BETWEEN_MESSAGES_TIME[message.author.id] = time.time() + 10

    @commands.Cog.listener()
    async def on_message_edit(self, before: nextcord.Message, after: nextcord.Message):
        await logstool.Logs(before.guild).edit_message(before, after)

    @commands.Cog.listener()
    async def on_message_delete(self, message: nextcord.Message):
        await logstool.pre_message_delete_log(message)

    @commands.Cog.listener()
    async def on_guild_audit_log_entry_create(self, entry: nextcord.AuditLogEntry):
        if entry.action != nextcord.AuditLogAction.message_delete or entry.target is None:
            return
        await logstool.set_message_delete_audit_log(entry.user, entry.extra.channel.id, entry.target.id)


def setup(bot):
    bot.add_cog(MessageEvent(bot))
