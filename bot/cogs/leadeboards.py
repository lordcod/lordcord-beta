
import nextcord
from nextcord.ext import commands

from typing import List, Optional, Self, TypeVar

from bot.languages import i18n
from bot.misc.lordbot import LordBot
from bot.misc.utils import get_award,  AsyncSterilization,  parse_fission

from bot.misc.time_transformer import display_time
from bot.views import menus
from bot.databases import GuildDateBases, EconomyMemberDB

PEDESTAL_IMAGE_URL = 'https://i.postimg.cc/CKGc5k1d/pedestal.png'
T = TypeVar("T")

state_parameters = {
    'messages': 'message_state',
    'score': 'score_state',
    'voicetime': 'voice_time_state',
}


def clear_empty_leaderboard_economy(guild: nextcord.Guild, leaderboard: list):
    for (member_id, balance, bank, total) in leaderboard.copy():
        member = guild._state.get_user(member_id)
        if not member or 0 >= total:
            try:
                leaderboard.remove(
                    (member_id, balance, bank, total))
            except ValueError:
                pass


def clear_empty_leaderboard(guild: nextcord.Guild, leaderboard: dict):
    get_user = guild._state.get_user
    for member_id, value in leaderboard.copy().items():
        member = get_user(member_id)
        if not member or 0 >= value:
            leaderboard.pop(member_id, None)


@AsyncSterilization
class PartialLeaderboardView(menus.Menus):
    embed: nextcord.Embed

    async def __init__(self, member: nextcord.Member, leaderboards: list, leaderboard_indexs: List[int], model: str) -> Self:
        guild = member.guild

        self.gdb = GuildDateBases(guild.id)
        self.color = await self.gdb.get('color')
        self.locale = await self.gdb.get('language')

        self.member = member
        self.guild = guild
        self.leaderboard_indexs = leaderboard_indexs

        try:
            self.user_index = leaderboard_indexs.index(member.id)+1
        except ValueError:
            self.user_index = len(leaderboard_indexs) + 1

        super().__init__(leaderboards, timeout=300)

        self.handler_disable()

        self.remove_item(self.button_previous)
        self.remove_item(self.button_next)

        self.add_item(await LeaderboardDropDown(guild.id, model))

        return self

    async def interaction_check(self, interaction: nextcord.Interaction) -> bool:
        return interaction.user == self.member

    async def callback(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await interaction.response.edit_message(embed=self.embed, view=self)


@AsyncSterilization
class EconomyLeaderboardView(PartialLeaderboardView.cls):
    async def __init__(self, *args) -> None:
        await super().__init__(*args, 'balance')

        economic_settings: dict = await self.gdb.get('economic_settings')
        self.currency_emoji = economic_settings.get('emoji')

    @property
    def embed(self) -> nextcord.Embed:
        embed = nextcord.Embed(
            title=i18n.t(self.locale, 'leaderboard.balance.embed.title'),
            description=i18n.t(self.locale, 'leaderboard.balance.embed.description',
                               member=self.member, user_index=self.user_index),
            color=self.color
        )
        embed.set_thumbnail(PEDESTAL_IMAGE_URL)
        embed.set_footer(
            text=self.guild.name,
            icon_url=self.guild.icon
        )

        leaderboard_indexs = self.leaderboard_indexs
        get_user = self.guild._state.get_user
        currency_emoji = self.currency_emoji
        for (member_id, balance, bank, total) in self.value[self.index]:
            member = get_user(member_id)
            index = leaderboard_indexs.index(member_id)+1
            award = get_award(index)
            embed.add_field(
                name=f"{award}. {member.display_name}",
                value=i18n.t(self.locale, 'leaderboard.balance.embed.field.value',
                             balance=balance, bank=bank,
                             total=total, currency_emoji=currency_emoji),
                inline=False
            )

        return embed


@AsyncSterilization
class StateLeaderboardView(PartialLeaderboardView.cls):
    async def __init__(self, state: str, *args) -> None:
        await super().__init__(*args, state)

        self.state = state

    @property
    def embed(self) -> nextcord.Embed:
        name = i18n.t(self.locale, f'leaderboard.{self.state}.name')
        embed = nextcord.Embed(
            title=i18n.t(self.locale, 'leaderboard.state.embed.title', name=name),
            description=i18n.t(self.locale, 'leaderboard.state.embed.description', member=self.member, user_index=self.user_index),
            color=self.color
        )
        embed.set_thumbnail(PEDESTAL_IMAGE_URL)
        embed.set_footer(
            text=self.guild.name,
            icon_url=self.guild.icon
        )

        get_user = self.guild._state.get_user
        leaderboard_indexs = self.leaderboard_indexs
        results = []
        for member_id, value in self.value[self.index]:
            member = get_user(member_id)
            index = leaderboard_indexs.index(member_id)+1
            award = get_award(index)
            parsed_value = self.parse_value(value)
            results.append(i18n.t(self.locale, 'leaderboard.state.embed.field.value', award=award, parsed_value=parsed_value, member=member))
        embed.add_field(
            name='',
            value=''.join(results)
        )

        return embed

    def parse_value(self, value: float | int):
        if self.state == 'voicetime':
            return display_time(value, max_items=1, with_rounding=True)
        if self.state == 'messages':
            return f'{value} messages'
        if self.state == 'score':
            return f'{value:.0f} points'
        raise TypeError("invalid state")


class LeaderboardTypes:
    def __init__(self, member: nextcord.Member, message: nextcord.Message) -> None:
        self.member = member
        self.guild = member.guild
        self.message = message

    async def parse_balance_lb(self):
        emdb = EconomyMemberDB(self.guild.id, self.member.id)
        leaderboard = await emdb.get_leaderboards()

        clear_empty_leaderboard_economy(self.guild, leaderboard)
        fission_leaderboards = parse_fission(leaderboard, 6)
        leaderboard_indexs = [self.member_id for (self.member_id, *_) in leaderboard]

        view = await EconomyLeaderboardView(
            self.member,
            fission_leaderboards,
            leaderboard_indexs
        )
        await self.message.edit(content=None, embed=view.embed, view=view)

    async def parse_voicetime_lb(self):
        await self._parse_state('voicetime')

    async def parse_messages_lb(self):
        await self._parse_state('messages')

    async def parse_score_lb(self):
        await self._parse_state('score')

    async def _parse_state(self, state: str):
        gdb = GuildDateBases(self.guild.id)
        state_db = await gdb.get(state_parameters[state])

        clear_empty_leaderboard(self.guild, state_db)
        fission_leaderboards = parse_fission(state_db.items(), 6)
        leaderboard_indexs = list(state_db.keys())

        view = await StateLeaderboardView(
            state,
            self.member,
            fission_leaderboards,
            leaderboard_indexs
        )
        await self.message.edit(content=None, embed=view.embed, view=view)


@AsyncSterilization
class LeaderboardDropDown(nextcord.ui.StringSelect):
    async def __init__(self, guild_id: int, selected_value: Optional[str] = None) -> None:
        gdb = GuildDateBases(guild_id)
        locale = await gdb.get('language')
        states = ['balance', 'voicetime', 'messages', 'score']

        super().__init__(
            options=[
                nextcord.SelectOption(
                    label=i18n.t(locale, f'leaderboard.{state}.name'),
                    value=state,
                    default=selected_value == state
                )
                for state in states
            ]
        )

    async def callback(self, interaction: nextcord.Interaction) -> None:
        gdb = GuildDateBases(interaction.guild_id)
        locale = await gdb.get('language')
        await interaction.response.edit_message(content=i18n.t(locale, 'leaderboard.loading'), embed=None, view=None)

        value = self.values[0]
        lbt = LeaderboardTypes(interaction.user, interaction.message)
        func = getattr(lbt, 'parse_'+value+'_lb')
        await func()


class Leaderboards(commands.Cog):
    def __init__(self, bot: LordBot) -> None:
        self.bot = bot

    @commands.command(name="leaderboard", aliases=["lb", "leaders", "top"])
    async def leaderboard(self, ctx: commands.Context):
        gdb = GuildDateBases(ctx.guild.id)
        locale = await gdb.get('language')
        message = await ctx.send(i18n.t(locale, 'leaderboard.loading'))
        await LeaderboardTypes(ctx.author, message).parse_balance_lb()


def setup(bot):
    bot.add_cog(Leaderboards(bot))
