
import logging
import nextcord
from nextcord.ext import commands
import nextcord.gateway
from nextcord.utils import escape_markdown


import random
import asyncio
import time
import orjson
from typing import Callable, Dict, List, Optional, Tuple, TypedDict, Union, Literal


from bot.databases import EconomyMemberDB, GuildDateBases
from bot.languages import i18n
from bot.misc.plugins import logstool
from bot.views.economy_shop import EconomyShopView
from bot.misc.lordbot import LordBot
from bot.misc.utils import TranslatorFlags, clamp, randfloat
from bot.resources.errors import InactiveEconomy
from bot.resources.ether import Emoji
from bot.misc.utils import BlackjackGame
from bot.resources.info import DEFAULT_ECONOMY_THEFT
from bot.views.blackjack import BlackjackView

_log = logging.getLogger(__name__)


class ArgumntRouletteItem(TypedDict):
    input_data_condition: Callable[[str], bool]
    random_condition: Callable[[str, int], bool]
    multiplier: int


timeout_rewards: Dict[str, int] = {
    "daily": 86400, "weekly": 604800, "monthly": 2592000}
roulette_games: Dict[int,
                     Tuple[
                         Callable[[], None],
                         List[Tuple[nextcord.Member, int, str]],
                         nextcord.Message]
                     ] = {}
arguments_roulette: List[ArgumntRouletteItem] = [
    {
        "input_data_condition": lambda val: val.isdigit() and 0 <= int(val) <= 36,
        "random_condition": lambda val, ran: ran == int(val),
        "multiplier": 35,
    },
    {
        "input_data_condition": lambda val: val == "1 to 12" or val.replace(" ", "") == "1-12",
        "random_condition": lambda val, ran: 1 <= ran <= 12,
        "multiplier": 3,
    },
    {
        "input_data_condition": lambda val: val == "13 to 24" or val.replace(" ", "") == "13-24",
        "random_condition": lambda val, ran: 13 <= ran <= 24,
        "multiplier": 3,
    },
    {
        "input_data_condition": lambda val: val == "25 to 36" or val.replace(" ", "") == "25-36",
        "random_condition": lambda val, ran: 25 <= ran <= 36,
        "multiplier": 3,
    },
    {
        "input_data_condition": lambda val: val == "1 to 18" or val.replace(" ", "") == "1-18",
        "random_condition": lambda val, ran: 1 <= ran <= 18,
        "multiplier": 2,
    },
    {
        "input_data_condition": lambda val: val == "19 to 36" or val.replace(" ", "") == "19-36",
        "random_condition": lambda val, ran: 19 <= ran <= 36,
        "multiplier": 2,
    },
    {
        "input_data_condition": lambda val: val == "red",
        "random_condition": lambda val, ran: ran in [1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36],
        "multiplier": 2,
    },
    {
        "input_data_condition": lambda val: val == "black",
        "random_condition": lambda val, ran: ran in [2, 4, 6, 8, 10, 11, 13, 15, 17, 20, 22, 24, 26, 28, 29, 31, 33, 35],
        "multiplier": 2,
    },
    {
        "input_data_condition": lambda val: val == "even",
        "random_condition": lambda val, ran: ran % 2 == 0,
        "multiplier": 2,
    },
    {
        "input_data_condition": lambda val: val == "odd",
        "random_condition": lambda val, ran: ran % 2 == 1,
        "multiplier": 2,
    },
    {
        "input_data_condition": lambda val: val == "1st",
        "random_condition": lambda val, ran: ran in [1, 4, 7, 10, 13, 16, 19, 22, 25, 28, 31, 34],
        "multiplier": 3,
    },
    {
        "input_data_condition": lambda val: val == "2nd",
        "random_condition": lambda val, ran: ran in [2, 5, 8, 11, 14, 17, 20, 23, 26, 29, 32, 35],
        "multiplier": 3,
    },
    {
        "input_data_condition": lambda val: val == "3rd",
        "random_condition": lambda val, ran: ran in [3, 6, 9, 12, 15, 18, 21, 24, 27, 30, 33, 36],
        "multiplier": 3
    },
]


def create_roulette_task():
    loop = asyncio.get_event_loop()
    future = loop.create_future()
    _task = loop.call_later(10, future.set_result, None)

    def wrapped():
        nonlocal _task
        _task.cancel()
        _task = loop.call_later(10, future.set_result, None)
    return future, wrapped


def is_valid_roulette_argument(val: str) -> bool:
    return any(data['input_data_condition'](val) for data in arguments_roulette)


with open("bot/languages/works.json", "rb") as file:
    list_of_works = orjson.loads(file.read())

timeout_rewards = {"daily": 86400, "weekly": 604800, "monthly": 2592000}


def check_prison():
    async def predicate(ctx: commands.Context) -> bool:
        gdb = GuildDateBases(ctx.guild.id)
        locale = await gdb.get('language')
        account = EconomyMemberDB(ctx.guild.id, ctx.author.id)
        conclusion = await account.get('conclusion')

        if not conclusion or time.time() > conclusion:
            return True

        await ctx.send(i18n.t(locale, 'economy.permission.prison', conclusion=conclusion))
        return False
    return commands.check(predicate)


class Economy(commands.Cog):
    def __init__(self, bot: LordBot) -> None:
        self.bot = bot
        super().__init__()

    async def cog_check(self, ctx: commands.Context):
        gdb = GuildDateBases(ctx.guild.id)
        es = await gdb.get('economic_settings')
        operate = es.get('operate', False)
        if not operate:
            raise InactiveEconomy("Economy is disabled on the server")
        return True

    async def handle_rewards(self, ctx: commands.Context):
        loctime = time.time()
        account = EconomyMemberDB(ctx.guild.id, ctx.author.id)
        gdb = GuildDateBases(ctx.guild.id)
        locale = await gdb.get('language')

        color = await gdb.get('color')
        economic_settings: dict = await gdb.get('economic_settings')
        currency_emoji = economic_settings.get('emoji')
        award = economic_settings.get(ctx.command.name, 0)
        reward_time = await account.get(ctx.command.name, 0)

        if award <= 0:
            await ctx.send(i18n.t(locale, 'economy.reward.error.unspecified'))
            return
        if loctime > reward_time:
            wait_long = loctime+timeout_rewards.get(ctx.command.name)

            embed = nextcord.Embed(
                title=i18n.t(locale, 'economy.reward.success.title'),
                description=i18n.t(locale, 'economy.reward.success.description',
                                   award=award, emoji=currency_emoji, wait_long=wait_long),
                color=color
            )
            await account.set(ctx.command.name, wait_long)
            await account.increment('balance', award)
            await logstool.Logs(ctx.guild).add_currency(ctx.author, award, reason=f'{ctx.command.name} reward')
        else:
            embed = nextcord.Embed(
                title=i18n.t(locale, 'economy.reward.error.early.title'),
                description=i18n.t(
                    locale, 'economy.reward.error.description.title', time=reward_time),
                color=color
            )

        await ctx.send(embed=embed)

    @commands.command(name='daily')
    @check_prison()
    async def daily(self, ctx: commands.Context):
        await self.handle_rewards(ctx)

    @commands.command(name='weekly')
    @check_prison()
    async def weekly(self, ctx: commands.Context):
        await self.handle_rewards(ctx)

    @commands.command(name='monthly')
    @check_prison()
    async def monthly(self, ctx: commands.Context):
        await self.handle_rewards(ctx)

    @commands.command(name='work')
    @check_prison()
    async def work(self, ctx: commands.Context):
        loctime = time.time()
        account = EconomyMemberDB(ctx.guild.id, ctx.author.id)
        gdb = GuildDateBases(ctx.guild.id)
        locale = await gdb.get('language')
        color = await gdb.get('color')
        work = await account.get('work', 0)
        economic_settings: dict = await gdb.get('economic_settings')
        currency_emoji = economic_settings.get('emoji')
        work_info = economic_settings.get('work')

        if loctime > work+work_info['cooldown']:
            amount = random.randint(work_info['min'], work_info['max'])

            embed = nextcord.Embed(
                title=i18n.t(locale, 'economy.work.success.title'),
                description=random.choice(
                    list_of_works.get(locale, list_of_works['en'])).format(amount=amount, emoji=currency_emoji),
                color=color
            )
            embed.add_field(
                name="",
                value=i18n.t(locale, 'economy.work.success.description',
                             time=loctime+work_info['cooldown'])
            )
            await account.set('work', loctime)
            await account.increment('balance', amount)
        else:
            embed = nextcord.Embed(
                title=i18n.t(locale, 'economy.work.error.early.title'),
                description=i18n.t(
                    locale, 'economy.work.error.early.description', time=work+work_info['cooldown']),
                color=color
            )
        await ctx.send(embed=embed)
        await logstool.Logs(ctx.guild).add_currency(ctx.author, amount, reason='part-time job')

    @commands.command(name="balance", aliases=["bal"])
    async def balance(self,
                      ctx: commands.Context,
                      member: Optional[nextcord.Member] = None):
        if not member:
            member = ctx.author

        loctime = time.time()

        gdb = GuildDateBases(ctx.guild.id)
        prefix = escape_markdown(await gdb.get('prefix'))
        locale = await gdb.get('language')
        color = await gdb.get('color')
        economic_settings: dict = await gdb.get('economic_settings')
        currency_emoji = economic_settings.get('emoji')

        account = EconomyMemberDB(ctx.guild.id, member.id)
        balance = await account.get('balance', 0)
        bank = await account.get('bank', 0)

        description = ""
        rewards = ['daily', 'weekly', 'monthly']
        for rw in rewards:
            if await account.get(rw, 0) < loctime:
                description += i18n.t(locale,
                                      'economy.balance.reward.'+rw, prefix=prefix)
        if description:
            description = i18n.t(
                locale, 'economy.balance.reward.available', description=description)

        embed = nextcord.Embed(
            title=i18n.t(locale, 'economy.balance.name'),
            color=color,
            description=description
        )
        embed.set_author(name=member.display_name,
                         icon_url=member.display_avatar)

        embed.add_field(
            name=i18n.t(locale, 'economy.balance.value.cash'),
            value=f'{balance :,}{currency_emoji}',
            inline=True
        )
        embed.add_field(
            name=i18n.t(locale, 'economy.balance.value.bank'),
            value=f'{bank :,}{currency_emoji}',
            inline=True
        )
        embed.add_field(
            name=i18n.t(locale, 'economy.balance.value.total'),
            value=f'{balance+bank :,}{currency_emoji}',
            inline=False
        )

        await ctx.send(embed=embed)

    @commands.command()
    @check_prison()
    async def shop(self, ctx: commands.Context):
        view = await EconomyShopView(ctx.guild)
        await ctx.send(embed=view.embed, view=view)

    @commands.command(name="pay")
    @check_prison()
    async def pay(self, ctx: commands.Context, member: nextcord.Member, amount: int):
        gdb = GuildDateBases(ctx.guild.id)
        color = await gdb.get('color')
        prefix = await gdb.get('prefix')
        locale = await gdb.get('language')
        economic_settings: dict = await gdb.get('economic_settings')
        currency_emoji = economic_settings.get('emoji')
        from_account = EconomyMemberDB(ctx.guild.id, ctx.author.id)
        to_account = EconomyMemberDB(ctx.guild.id, member.id)

        if amount <= 0:
            await ctx.send(i18n.t(locale, 'economy.pay.error.negative'))
            return
        elif amount > await from_account.get('balance', 0):
            await ctx.send(i18n.t(locale, 'economy.pay.error.unenough', prefix=prefix))
            return

        embed = nextcord.Embed(
            title=i18n.t(locale, 'economy.pay.success.title'),
            description=i18n.t(locale, 'economy.pay.success.description', author=ctx.author.name,
                               member=member.name, amount=amount, emoji=currency_emoji),
            color=color,
        )
        embed.set_thumbnail(ctx.author.display_avatar)

        await from_account.decline("balance", amount)
        await to_account.increment("balance", amount)

        await logstool.Logs(ctx.guild).add_currency(member, amount, reason=f'received from a {ctx.author.name} member')
        await logstool.Logs(ctx.guild).remove_currency(ctx.author, amount, reason=f'passed to the {member.name} participant')
        await ctx.send(embed=embed)

    @commands.command(name="deposit", aliases=["dep"])
    @check_prison()
    async def deposit(self, ctx: commands.Context, amount: Union[Literal['all'], int]):
        gdb = GuildDateBases(ctx.guild.id)
        color = await gdb.get('color')
        prefix = await gdb.get('prefix')
        economic_settings: dict = await gdb.get('economic_settings')
        currency_emoji = economic_settings.get('emoji')
        account = EconomyMemberDB(ctx.guild.id, ctx.author.id)
        balance = await account.get('balance', 0)
        locale = await gdb.get('language')

        if amount == "all":
            amount = balance
        if amount <= 0:
            await ctx.send(i18n.t(locale, 'economy.deposit.error.negative'))
            return
        if amount > balance:
            await ctx.send(i18n.t(locale, 'economy.deposit.error.unenough', prefix=prefix))
            return

        await account.decline('balance', amount)
        await account.increment('bank', amount)

        embed = nextcord.Embed(
            title=i18n.t(locale, 'economy.deposit.success.title'),
            color=color,
            description=i18n.t(
                locale, 'economy.deposit.success.description', amount=amount, emoji=currency_emoji)
        )
        embed.set_thumbnail(ctx.author.display_avatar)
        await ctx.send(embed=embed)

    @commands.command(name="withdraw", aliases=["wd"])
    @check_prison()
    async def withdraw(self, ctx: commands.Context, amount: Union[Literal['all'], int]):
        gdb = GuildDateBases(ctx.guild.id)
        color = await gdb.get('color')
        prefix = await gdb.get('prefix')
        economic_settings: dict = await gdb.get('economic_settings')
        currency_emoji = economic_settings.get('emoji')
        account = EconomyMemberDB(ctx.guild.id, ctx.author.id)
        bank = await account.get('bank', 0)
        locale = await gdb.get('language')

        if amount == "all":
            amount = bank
        if amount <= 0:
            await ctx.send(i18n.t(locale, 'economy.withdraw.error.negative'))
            return
        if amount > bank:
            await ctx.send(i18n.t(locale, 'economy.withdraw.error.unenough', prefix=prefix))
            return

        await account.increment('balance', amount)
        await account.decline('bank', amount)

        embed = nextcord.Embed(
            title=i18n.t(locale, 'economy.withdraw.success.title'),
            color=color,
            description=i18n.t(
                locale, 'economy.withdraw.success.description', amount=amount, emoji=currency_emoji)
        )
        embed.set_thumbnail(ctx.author.display_avatar)
        await ctx.send(embed=embed)

    @commands.command(name="gift")
    @commands.has_permissions(administrator=True)
    async def gift(self, ctx: commands.Context, member: Optional[Union[nextcord.Member, nextcord.Role]], amount: int, *, flags: TranslatorFlags['bank'] = {}):
        if not member:
            member = ctx.author

        gdb = GuildDateBases(ctx.guild.id)
        economic_settings: dict = await gdb.get('economic_settings')
        currency_emoji = economic_settings.get('emoji')
        locale = await gdb.get('language')

        if 0 >= amount:
            await ctx.send(i18n.t(locale, 'economy.gift.error.negative'))
            return

        if isinstance(member, nextcord.Role):
            member_ids = [m.id for m in member.members]
            if flags.get('bank'):
                await EconomyMemberDB.increment_for_ids(ctx.guild.id, member_ids, 'bank', amount)
            else:
                await EconomyMemberDB.increment_for_ids(ctx.guild.id, member_ids, 'balance', amount)
            await ctx.send(i18n.t(locale, 'economy.gift.success.role', amount=amount, emoji=currency_emoji, role=member.name))
            await logstool.Logs(ctx.guild).add_currency_for_ids(member, amount, moderator=ctx.author)
        else:
            account = EconomyMemberDB(ctx.guild.id, member.id)
            if flags.get('bank'):
                await account.increment('bank', amount)
            else:
                await account.increment('balance', amount)
            await ctx.send(i18n.t(locale, 'economy.gift.success.member', amount=amount, emoji=currency_emoji, member=member.name))
            await logstool.Logs(ctx.guild).add_currency(member, amount, moderator=ctx.author)

    @commands.command(name="take")
    @commands.has_permissions(administrator=True)
    async def take(self, ctx: commands.Context, member: Optional[nextcord.Member], amount: Union[Literal['all'], int], *, flags: TranslatorFlags['bank'] = {}):
        if not member:
            member = ctx.author

        gdb = GuildDateBases(ctx.guild.id)
        locale = await gdb.get('language')
        economic_settings: dict = await gdb.get('economic_settings')
        currency_emoji = economic_settings.get('emoji')
        account = EconomyMemberDB(ctx.guild.id, member.id)
        bank = await account.get('bank')
        balance = await account.get('balance')

        if amount != 'all' and 0 >= amount:
            await ctx.send(i18n.t(locale, 'economy.take.error.negative'))
            return

        if flags.get('bank'):
            if amount == 'all':
                amount = bank
            if amount > bank:
                await ctx.send(i18n.t(locale, 'economy.take.error.bank.unenough'))
                return

            await account.decline('bank', amount)
        else:
            if amount == 'all':
                amount = balance
            if amount > balance:
                await ctx.send(i18n.t(locale, 'economy.take.error.balance.unenough'))
                return

            await account.decline('balance', amount)

        await ctx.send(i18n.t(locale, 'economy.take.success', amount=amount, emoji=currency_emoji, member=member.name))
        await logstool.Logs(ctx.guild).remove_currency(member, amount, moderator=ctx.author)

    @commands.command()
    @check_prison()
    async def rob(self, ctx: commands.Context, member: nextcord.Member):
        gdb = GuildDateBases(ctx.guild.id)
        locale = await gdb.get('language')
        color = await gdb.get('color')
        economic_settings: dict = await gdb.get('economic_settings')
        currency_emoji = economic_settings.get('emoji')
        theft_data = economic_settings.get('theft', DEFAULT_ECONOMY_THEFT)
        scope = (theft_data['time_prison']['max'] -
                 theft_data['time_prison']['min']
                 ) / theft_data['time_prison']['adaptive']

        if not theft_data['jail']:
            await ctx.send(i18n.t(locale, 'economy.rob.disabled'))
            return

        conclusion = (
            time.time() +
            theft_data['time_prison']['adaptive'] *
            random.randint(1, scope+1)
        )
        thief_account = EconomyMemberDB(ctx.guild.id, ctx.author.id)
        victim_account = EconomyMemberDB(ctx.guild.id, member.id)

        thief_rob = await thief_account.get('rob')
        thief_balance = await thief_account.get('balance')
        victim_balance = await victim_account.get('balance')

        if thief_rob+theft_data['cooldown'] > time.time():
            embed = nextcord.Embed(
                title=i18n.t(locale, 'economy.rob.title'),
                description=i18n.t(locale, '', member=ctx.author,
                                   time=thief_rob+theft_data['cooldown']),
                color=color
            )
            embed.set_thumbnail(ctx.author.display_avatar)
            await ctx.send(embed=embed)
            return

        await thief_account.set('rob', time.time())
        win_chance = clamp(
            0.1, thief_balance/(victim_balance+thief_balance), 0.75)
        if member.status != nextcord.Status.offline:
            win_chance -= 0.05
        chance = random.random()
        if win_chance > chance:
            debt = win_chance * \
                victim_balance * 1/2
            if debt >= thief_balance:
                calculated_debt = (
                    thief_balance * .6
                    * debt * .2
                    * randfloat(.8, 1.2)
                )
                embed = nextcord.Embed(
                    title=i18n.t(locale, 'economy.rob.title'),
                    description=i18n.t(locale, 'economy.rob.success.mini',
                                       author=ctx.author.name,
                                       member=member.name,
                                       calculated_debt=calculated_debt,
                                       debt=debt,
                                       emoji=currency_emoji),
                    color=color
                )

                await thief_account.increment('balance', calculated_debt)
                await victim_account.decline('balance', debt)
                await logstool.Logs(ctx.guild).add_currency(ctx.author, calculated_debt, reason='a successful attempt at theft')
                await logstool.Logs(ctx.guild).remove_currency(member, debt, reason='a successful attempt at theft')
            else:
                embed = nextcord.Embed(
                    title=i18n.t(locale, 'economy.rob.title'),
                    description=i18n.t(locale, 'economy.rob.success.full',
                                       author=ctx.author.name,
                                       member=member.name,
                                       debt=debt,
                                       emoji=currency_emoji),
                    color=color
                )

                await thief_account.increment('balance', debt)
                await victim_account.decline('balance', debt)
                await logstool.Logs(ctx.guild).add_currency(ctx.author, debt, reason='a successful attempt at theft')
                await logstool.Logs(ctx.guild).remove_currency(member, debt, reason='a successful attempt at theft')
        else:
            debt = (1-win_chance) * thief_balance * 1/2
            embed = nextcord.Embed(
                title=i18n.t(locale, 'economy.rob.title'),
                description=i18n.t(locale, 'economy.rob.success.failure',
                                   author=ctx.author.name,
                                   member=member.name,
                                   debt=debt,
                                   emoji=currency_emoji,
                                   conclusion=conclusion),
                color=color
            )

            await thief_account.set('conclusion', conclusion)
            await victim_account.decline('balance', debt)
            await logstool.Logs(ctx.guild).remove_currency(ctx.author, debt, reason='a failed theft attempt')
        embed.set_thumbnail(ctx.author.display_avatar)
        await ctx.send(embed=embed)

    @commands.command(name="roulette", aliases=["rou"])
    async def roulette(self, ctx: commands.Context, amount: int, *, val: str):
        val = val.lower()
        gdb = GuildDateBases(ctx.guild.id)
        account = EconomyMemberDB(ctx.guild.id, ctx.author.id)
        prefix = await gdb.get('prefix')
        locale = await gdb.get('language')
        color = await gdb.get('color')
        balance = await account.get('balance')
        economic_settings: dict = await gdb.get('economic_settings')
        currency_emoji = economic_settings.get('emoji')
        bet_info = economic_settings.get('bet')
        _min_bet = bet_info.get('min')
        _max_bet = bet_info.get('max')

        if not is_valid_roulette_argument(val):
            await ctx.send(i18n.t(locale, "economy.roulette.error.invalid", prefix=prefix))
            return
        if amount <= 0:
            await ctx.send(i18n.t(locale, "economy.roulette.error.negative"))
            return
        if amount > balance:
            await ctx.send(i18n.t(locale, "economy.roulette.error.unenough", prefix=prefix))
            return
        if not _max_bet >= amount >= _min_bet:
            await ctx.send(i18n.t(locale, "economy.roulette.error.limit",
                                  max_bet=_max_bet,
                                  min_bet=_min_bet,
                                  emoji=currency_emoji,
                                  amount=amount))
            return

        await account.decline("balance", amount)
        await logstool.Logs(ctx.guild).remove_currency(ctx.author, amount, reason='the beginning of the roulette game')

        if rg := roulette_games.get(ctx.guild.id):
            postpone, listener, mes = rg
            postpone()
            listener.append((ctx.author, amount, val))
            embed = nextcord.Embed(
                title=i18n.t(locale, 'economy.roulette.game.title'),
                description='\n'.join(
                    [i18n.t(locale, 'economy.roulette.game.description',
                            member=member.name,
                            amount=amount,
                            emoji=currency_emoji,
                            value=val)
                     for member, amount, val in listener]),
                color=color
            )
            embed.set_author(name=ctx.guild.name,
                             icon_url=ctx.guild.icon)
            embed.set_footer(
                text=i18n.t(locale, 'economy.roulette.game.footer'))
            asyncio.create_task(mes.edit(embed=embed))
            if ctx.channel == mes.channel:
                asyncio.create_task(ctx.message.add_reaction(Emoji.success))
            else:
                asyncio.create_task(
                    ctx.send(i18n.t(locale, 'economy.roulette.game.got', url=mes.jump_url)))
            return
        else:
            embed = nextcord.Embed(
                title=i18n.t(locale, 'economy.roulette.game.title'),
                description=i18n.t(locale, 'economy.roulette.game.description',
                                   member=ctx.author.name,
                                   amount=amount,
                                   emoji=currency_emoji,
                                   value=val),
                color=color
            )
            embed.set_author(name=ctx.guild.name,
                             icon_url=ctx.guild.icon)
            embed.set_footer(
                text=i18n.t(locale, 'economy.roulette.game.footer'))
            mes = await ctx.send(embed=embed)

            listener = [(ctx.author, amount, val)]
            future, postpone = create_roulette_task()
            roulette_games[ctx.guild.id] = (
                postpone, listener, mes)

            try:
                await asyncio.wait_for(future, timeout=60)
            except asyncio.TimeoutError:
                pass

        roulette_games.pop(ctx.guild.id, None)
        ran = random.randint(1, 36)
        results = []
        wins = []
        for _member, _amount, _arg in listener:
            for roulette_item in arguments_roulette:
                if roulette_item["input_data_condition"](_arg):
                    account = EconomyMemberDB(ctx.guild.id, _member.id)
                    if roulette_item["random_condition"](_arg, ran):
                        results.append(i18n.t(locale, 'economy.roulette.game.result.win',
                                              member=_member.name,
                                              amount=_amount *
                                              roulette_item['multiplier'],
                                              emoji=currency_emoji))
                        wins.append(
                            (_member.name, _amount*roulette_item['multiplier']))
                        await account.increment(
                            "balance", _amount * roulette_item["multiplier"])
                        await logstool.Logs(ctx.guild).add_currency(_member,
                                                                    _amount *
                                                                    roulette_item["multiplier"],
                                                                    reason='the game of roulette won')
                    else:
                        results.append(i18n.t(locale, 'economy.roulette.game.result.lost',
                                              member=_member.name,
                                              amount=_amount,
                                              emoji=currency_emoji))
                    break

        win_color = 'red' if arguments_roulette[6]["random_condition"](
            0, ran) else 'black'

        description = '\n'.join(results)
        if wins:
            description += '\n\n'+i18n.t(locale, 'economy.roulette.game.result.wins.success',
                                         wins=', '.join(dict(wins).keys()),
                                         amount=sum([w[1] for w in wins]),
                                         emoji=currency_emoji)
        else:
            description += '\n\n' + \
                i18n.t(locale, 'economy.roulette.game.result.wins.failed')

        embed = nextcord.Embed(
            title=i18n.t(locale, 'economy.roulette.game.result.ball',
                         win_color=win_color, ran=ran),
            description=description,
            color=color
        )
        embed.set_author(name=ctx.guild.name,
                         icon_url=ctx.guild.icon)
        await mes.edit(embed=embed)

    @commands.command(name="blackjack", aliases=["bj"])
    async def blackjack(self, ctx: commands.Context, amount: int):
        gdb = GuildDateBases(ctx.guild.id)
        prefix = await gdb.get('prefix')
        locale = await gdb.get('language')
        economic_settings: dict = await gdb.get('economic_settings')
        currency_emoji = economic_settings.get('emoji')
        bet_info = economic_settings.get('bet')
        _min_bet = bet_info.get('min')
        _max_bet = bet_info.get('max')
        account = EconomyMemberDB(ctx.guild.id, ctx.author.id)
        balance = await account.get('balance')

        if amount <= 0:
            await ctx.send(i18n.t(locale, "economy.roulette.error.negative"))
            return
        if amount > balance:
            await ctx.send(i18n.t(locale, "economy.roulette.error.unenough", prefix=prefix))
            return
        if not _max_bet >= amount >= _min_bet:
            await ctx.send(i18n.t(locale, "economy.roulette.error.limit",
                                  max_bet=_max_bet,
                                  min_bet=_min_bet,
                                  emoji=currency_emoji,
                                  amount=amount))
            return

        bjg = BlackjackGame(ctx.author, amount)
        await account.decline("balance", amount)
        await logstool.Logs(ctx.guild).remove_currency(ctx.author, amount, reason='the beginning of the blackjack game')

        if bjg.is_avid_winner() is not None:
            embed = await bjg.completed_embed()
            await ctx.send(embed=embed)
            match bjg.is_avid_winner():
                case 2:
                    await account.increment("balance", amount)
                    await logstool.Logs(ctx.guild).add_currency(ctx.author, amount, reason='draw at blackjack')
                case 1:
                    await account.increment("balance", 3.5*amount)
                    await logstool.Logs(ctx.guild).add_currency(ctx.author, amount, reason='a golden point in blackjack. victory')
            bjg.complete()
            return

        embed = await bjg.embed()
        view = BlackjackView(bjg)
        await ctx.send(embed=embed, view=view)

    @staticmethod
    def get_slots_embed(member: nextcord.Member, color: int, results: list) -> nextcord.Embed:
        embed = nextcord.Embed(
            title='S L O T S',
            description='\n'.join(' | '.join(res) for res in results),
            color=color
        )
        embed.set_footer(text=member, icon_url=member.display_avatar)
        return embed

    @commands.command()
    async def slots(self, ctx: commands.Context):
        gdb = GuildDateBases(ctx.guild.id)
        color = await gdb.get('color')

        emojis = ["⭐", "7️⃣", "💰", "🫡", "💀", "🎁", "🎉", "🥺"]
        results = (
            ['◾', '◾', '◾'],
            ['◾', '◾', '◾'],
            ['◾', '◾', '◾']
        )

        embed = self.get_slots_embed(ctx.author, color, results)
        message = await ctx.send(embed=embed)

        for _ in range(6):
            await asyncio.sleep(0.4)
            results = (
                [random.choice(emojis) for _ in range(3)],
                results[0],
                results[1]
            )
            embed = self.get_slots_embed(ctx.author, color, results)
            await message.edit(embed=embed)

        await asyncio.sleep(0.55)

        results[2][1] = results[1][1]
        results[1][1] = results[0][1]
        results[0][1] = random.choice(emojis)

        results[2][2] = results[1][2]
        results[1][2] = results[0][2]
        results[0][2] = random.choice(emojis)

        embed = self.get_slots_embed(ctx.author, color, results)
        await message.edit(embed=embed)

        await asyncio.sleep(0.7)

        results[2][2] = results[1][2]
        results[1][2] = results[0][2]
        results[0][2] = random.choice(emojis)

        embed = self.get_slots_embed(ctx.author, color, results)
        await message.edit(embed=embed)


def setup(bot):
    bot.add_cog(Economy(bot))
