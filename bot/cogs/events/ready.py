import logging
import os
from typing import Dict
from nextcord.ext import commands
import orjson

from bot.databases.handlers.guildHD import GuildDateBases
from bot.databases.varstructs import GiveawayData
from bot.languages.help import get_command
from bot.databases import RoleDateBases, BanDateBases
from bot.misc.plugins.giveaway import Giveaway
from bot.misc.lordbot import LordBot
from bot.misc.utils import AsyncSterilization
from bot.resources import ether
from bot.resources.ether import ColorType
from bot.views.delete_message import DeleteMessageView
from bot.views.giveaway import GiveawayView
from bot.views.ideas import ConfirmView, IdeaView, ReactionConfirmView

import time
import asyncio

from bot.views.tempvoice.view import TempVoiceView
from bot.views.tempvoice.dropdown import AdvancedTempVoiceView
from bot.views.tickets.closes import CloseTicketView
from bot.views.tickets.delop import ControllerTicketView
from bot.views.tickets.faq import FAQView
_log = logging.getLogger(__name__)


class ReadyEvent(commands.Cog):
    def __init__(self, bot: LordBot) -> None:
        self.bot = bot
        bot.set_event(self.on_shard_disconnect)
        bot.set_event(self.on_disconnect)
        super().__init__()

    async def on_disconnect(self):
        _log.critical("Bot is disconnect")

    async def on_shard_disconnect(self, shard_id: int):
        _log.critical("Bot is disconnect (ShardId:%d)", shard_id)

    @commands.Cog.listener()
    async def on_ready(self):
        results = await asyncio.gather(
            self.add_views(),
            self.get_emojis(),
            self.find_not_data_commands(),
            self.process_temp_roles(),
            self.process_temp_bans(),
            self.process_giveaways(),
            self.process_guild_delete_tasks(),
            self.process_auto_load_commands_data(),
            return_exceptions=True
        )
        for i, res in enumerate(results, start=1):
            if isinstance(res, Exception):
                _log.debug(
                    '[%d][%s] Launching the bot was error: %s', i, type(res), res)

        _log.info(f"The bot is registered as {self.bot.user}")

    async def add_views(self):
        views = [ControllerTicketView, CloseTicketView, FAQView, ConfirmView,
                 ReactionConfirmView, IdeaView, GiveawayView, TempVoiceView,
                 AdvancedTempVoiceView, DeleteMessageView]
        for view in views:
            if isinstance(view, AsyncSterilization):
                rs = await view()
            else:
                rs = view()
            self.bot.add_view(rs)

    async def get_emojis(self):
        values = {}
        json_values = {}
        names = ('aqua', 'mala', 'barh', 'lava',
                 'perl', 'yant', 'sume', 'sliv')

        def get_color(name: str) -> str:
            for prefix in names:
                if name.startswith(prefix):
                    return prefix

        for emoji in self.bot.emojis:
            if emoji.name.startswith(names):
                color = get_color(emoji.name)
                name = emoji.name.removeprefix(color)

                values.setdefault(name, {})
                json_values.setdefault(name, {})
                values[name][ColorType.get(color).value] = str(emoji)
                json_values[name][color] = str(emoji)

        ether.every_emojis.update(values)
        with open('emojis.json', 'wb+') as file:
            file.write(orjson.dumps(json_values))

        for name, emojis in json_values.items():
            missing = set(names)-set(emojis.keys())
            if missing:
                _log.trace('Emojis were not found in %s: %s', name, missing)

    async def find_not_data_commands(self):
        cmd_wnf = []
        for cmd in self.bot.commands:
            cmd_data = get_command(cmd.qualified_name)
            if cmd_data is None and cmd.cog_name != 'Teams':
                cmd_wnf.append(cmd.qualified_name)

        if cmd_wnf:
            _log.info(
                f"Was not found command information: {', '.join(cmd_wnf)}")

    async def process_auto_load_commands_data(self):
        from bot.languages.help import get_command
        if not os.path.exists('auto'):
            os.mkdir('auto')

        commands = []
        for cmd in self.bot.commands:
            cmd_data = get_command(cmd.name)
            if cmd_data is None:
                cmd_data = {}

            if cmd_data.get('category') == 'interactions':
                continue

            cmd_params = len(cmd.params or [])-2
            if cmd_data.get('count_args', cmd_params) != cmd_params:
                _log.debug(
                    '[%s] %d/%d The number of arguments in the command does not match the documentation',
                    cmd.name,
                    cmd_data.get('count_args', cmd_params),
                    cmd_params
                )

            cmd_aliases = list(cmd.aliases or [])
            if len(cmd_aliases) != len(cmd_data.get('aliases', cmd_aliases)):
                _log.debug(
                    '[%s] The number of aliases in the command does not match the documentation', cmd.name)

            data = {
                'name': cmd.name,
                'category': cmd_data.get('category', cmd.cog_name),
                'aliases': cmd_aliases,
                'allowed_disabled': cmd_data.get('allowed_disabled', not cmd.enabled),
                'count_args': cmd_params,
                'count_examples': cmd_data.get('count_examples', 0)
            }
            commands.append(data)

        commands.sort(key=lambda item: item['category'])

        with open('auto/commands.json', 'wb+') as file:
            file.write(orjson.dumps(commands))

        _log.debug('Loaded commands data')

    async def process_temp_bans(self):
        bsdb = BanDateBases()
        data = await bsdb.get_all()

        for (guild_id, member_id, ban_time) in data:
            mbrsd = BanDateBases(guild_id, member_id)
            self.bot.lord_handler_timer.create(
                ban_time-time.time(), mbrsd.remove_ban(self.bot._connection), f"ban:{guild_id}:{member_id}")

    async def process_temp_roles(self):
        rsdb = RoleDateBases()
        data = await rsdb.get_all()

        for (guild_id, member_id, role_id, role_time) in data:
            if not (
                (guild := self.bot.get_guild(guild_id))
                and (member := guild.get_member(member_id))
                and (role := guild.get_role(role_id))
            ):
                continue

            mrsdb = RoleDateBases(guild_id, member_id)

            self.bot.lord_handler_timer.create(
                role_time-time.time(), mrsdb.remove_role(member, role), f"role:{guild_id}:{member_id}:{role_id}")

    async def process_giveaways(self):
        for guild in self.bot.guilds:
            gdb = GuildDateBases(guild.id)
            giveaways: Dict[int, GiveawayData] = await gdb.get('giveaways', {})
            for id, data in giveaways.items():
                if data['completed']:
                    continue
                gw = Giveaway(guild, id)
                gw.giveaway_data = data
                self.bot.lord_handler_timer.create(
                    gw.giveaway_data.get('date_end')-time.time(),
                    gw.complete(),
                    f'giveaway:{id}'
                )

    async def process_guild_delete_tasks(self):
        ...


def setup(bot):
    bot.add_cog(ReadyEvent(bot))
