import logging
from typing import Dict
from nextcord.ext import commands
import orjson

from bot.databases.handlers.guildHD import GuildDateBases
from bot.databases.varstructs import GiveawayData
from bot.languages.help import get_command
from bot.databases import RoleDateBases, BanDateBases
from bot.misc.giveaway import Giveaway
from bot.misc.lordbot import LordBot
from bot.misc.utils import AsyncSterilization
from bot.resources import ether
from bot.resources.ether import ColorType
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
        await asyncio.gather(
            self.add_views(),
            self.get_emojis(),
            self.find_not_data_commands(),
            self.process_temp_roles(),
            self.process_temp_bans(),
            self.process_giveaways(),
            self.process_guild_delete_tasks(),
        )

        _log.info(f"The bot is registered as {self.bot.user}")

    async def add_views(self):
        views = [ControllerTicketView, CloseTicketView, FAQView, ConfirmView,
                 ReactionConfirmView, IdeaView, GiveawayView, TempVoiceView, AdvancedTempVoiceView]
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
