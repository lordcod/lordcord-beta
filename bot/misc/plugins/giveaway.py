import asyncio
import nextcord
from typing import Coroutine, Any, Dict
from bot.databases.datastore import DataStore
from bot.databases.handlers.economyHD import EconomyMemberDB
from bot.databases.varstructs import GiveawayData
from bot.databases import GuildDateBases
from bot.misc import utils
from bot.views import giveaway as views_giveaway


class GiveawayTypesChecker:
    def __new__(cls) -> None:
        return None

    def __init__(self, types: Dict[int, Any], giveaway: 'GiveawayData', member: nextcord.Member) -> None:
        self.member = member
        self.giveaway_data = giveaway
        self.types = types

    def check_count_invites(self):
        return True

    def check_date_join(self):
        return self.member.joined_at.timestamp() >= self.types[1]

    def check_min_balance(self):
        emdb = EconomyMemberDB(self.member.guild.id, self.member.id)
        balance = emdb.get('balance')
        bank = emdb.get('bank')
        return balance + bank >= self.types[2]

    def check_guild_connect(self):
        ofter_guild = self.member._state._get_guild(self.types[3])
        return True if ofter_guild.get_member(self.member.id) else False

    def check_voice_connect(self):
        return True if self.member.voice else False

    def check_min_voice_time(self):
        return VOICE_STATE_DB.get(self.member.id) >= self.types[5]

    def check_min_level(self): ...

    types_function = {
        0: check_count_invites,
        1: check_date_join,
        2: check_min_balance,
        3: check_guild_connect,
        4: check_voice_connect,
        5: check_min_voice_time,
        6: check_min_level
    }


class GiveawayConfig:
    prize: str = None
    sponsor: nextcord.Member = None
    channel: nextcord.TextChannel = None
    description: str = None
    quantity: int = 1
    date_end: int | float = None


class Giveaway:
    giveaway_data: GiveawayData

    def __init__(
        self,
        guild: nextcord.Guild,
        message_id: int
    ) -> None:
        self.guild = guild
        self.message_id = message_id
        self.gdb = GuildDateBases(guild.id)

    async def fetch_giveaway_data(self) -> None:
        self.giveaways = await self.gdb.get('giveaways')
        self.giveaway_data = self.giveaways.get(self.message_id)

    async def update_giveaway_data(self, giveaway_data: GiveawayData) -> None:
        self.giveaways = await self.gdb.get('giveaways')
        self.giveaways[self.message_id] = giveaway_data
        await self.gdb.set('giveaways', self.giveaways)

    @classmethod
    async def create(
        cls,
        guild: nextcord.Guild,
        channel: nextcord.TextChannel,
        sponser: nextcord.Member,
        prize: str,
        description: str,
        quantity: int,
        date_end: int
    ) -> 'Giveaway':
        gdb = GuildDateBases(guild.id)
        giveaways = await gdb.get('giveaways')
        key, token = utils.generate_random_token()

        giveaway_data = {
            "guild_id": guild.id,
            "channel_id": channel.id,
            "sponsor_id": sponser.id,
            "prize": prize,
            "description": description,
            "quantity": quantity,
            "date_end": date_end,
            "types": [],
            "entries_ids": [],
            "completed": False,
            "winners": None,
            "key": key,
            "token": token
        }

        embed = cls.get_embed(giveaway_data)
        message = await channel.send(embed=embed, view=views_giveaway.GiveawayView())

        giveaways[message.id] = giveaway_data
        await gdb.set('giveaways', giveaways)

        return cls(guild, message.id)

    @classmethod
    def create_as_config(
        cls,
        guild: nextcord.Guild,
        giveaway_config: GiveawayConfig
    ) -> Coroutine[Any, Any, 'Giveaway']:
        return cls.create(
            guild=guild,
            channel=giveaway_config.channel,
            sponser=giveaway_config.sponsor,
            prize=giveaway_config.prize,
            description=giveaway_config.description,
            quantity=giveaway_config.quantity,
            date_end=giveaway_config.date_end
        )

    async def complete(self) -> None:
        await self.fetch_giveaway_data()

        # TODO: REFACTOING AND FIX
        winner_number = utils.decrypt_token(
            self.giveaway_data.get('key'), self.giveaway_data.get('token'))
        winner_ids = []
        entries_ids = self.giveaway_data.get('entries_ids').copy()

        if not entries_ids:
            return

        for _ in range(self.giveaway_data.get('quantity')):
            win = entries_ids.pop(winner_number % len(entries_ids))
            winner_ids.append(win)

        winners = map(self.guild.get_member,
                      winner_ids)

        self.giveaway_data['winners'] = winner_ids
        self.giveaway_data['completed'] = True
        await self.update_giveaway_data(self.giveaway_data)

        channel = self.guild.get_channel(self.giveaway_data.get('channel_id'))
        gw_message = channel.get_partial_message(self.message_id)

        asyncio.create_task(self.update_message())
        asyncio.create_task(channel.send(
            f"Congratulations {', '.join([wu.mention for wu in winners])}! You won the {self.giveaway_data['prize']}!",
            reference=gw_message))

    async def update_message(self) -> None:
        await self.fetch_giveaway_data()

        channel = self.guild.get_channel(self.giveaway_data.get('channel_id'))
        message = channel.get_partial_message(self.message_id)
        embed = self.get_completed_embed() if self.giveaway_data.get(
            'completed') else self.get_embed(self.giveaway_data)
        view = views_giveaway.GiveawayView(
        ) if not self.giveaway_data.get('completed') else None

        await message.edit(embed=embed, view=view)

    @staticmethod
    def get_embed(giveaway_data: dict) -> nextcord.Embed:
        giveaway_description = giveaway_data.get(
            'description')+'\n\n' if giveaway_data.get('description') else ''
        embed = nextcord.Embed(
            title=giveaway_data.get("prize"),
            description=(
                f"{giveaway_description}"
                f"Ends: <t:{giveaway_data.get('date_end'):.0f}:f> (<t:{giveaway_data.get('date_end'):.0f}:R>)\n"
                f"Sponsored by <@{giveaway_data.get('sponsor_id')}>\n"
                f"Entries: **{len(giveaway_data.get('entries_ids'))}**\n"
                f"Winners: **{giveaway_data.get('quantity')}**"
            )
        )

        return embed

    def get_completed_embed(self) -> nextcord.Embed:
        winners = filter(lambda item: item is not None,
                         map(self.guild.get_member,
                             self.giveaway_data.get('winners')))
        giveaway_description = self.giveaway_data.get(
            'description')+'\n\n' if self.giveaway_data.get('description') else ''
        embed = nextcord.Embed(
            title=self.giveaway_data.get("prize"),
            description=(
                f"{giveaway_description}"
                f"Ends: <t:{self.giveaway_data.get('date_end'):.0f}:f> (<t:{self.giveaway_data.get('date_end'):.0f}:R>)\n"
                f"Sponsored by <@{self.giveaway_data.get('sponsor_id')}>\n"
                f"Entries: **{len(self.giveaway_data.get('entries_ids'))}**\n"
                f"Winners: **{', '.join([wu.mention for wu in winners])}**"
            )
        )

        return embed

    async def check_participation(self, member_id: int) -> bool:
        await self.fetch_giveaway_data()
        return member_id in self.giveaway_data.get('entries_ids')

    async def promote_participant(self, member_id: int) -> None:
        await self.fetch_giveaway_data()
        self.giveaway_data.get('entries_ids').append(member_id)
        await self.update_giveaway_data(self.giveaway_data)

    async def demote_participant(self, member_id: int) -> None:
        await self.fetch_giveaway_data()
        self.giveaway_data.get('entries_ids').remove(member_id)
        await self.update_giveaway_data(self.giveaway_data)
