import random
import logging
from typing import List, Optional, Dict

import nextcord
import orjson

from bot.databases import GuildDateBases
from bot.resources.ether import Emoji
from .misc import randquan

_log = logging.getLogger(__name__)
_blackjack_games = {}

with open('assets/cards.json', 'rb') as file:
    CARDS: Dict[str, Optional[int]] = orjson.loads(file.read())


class BlackjackGame:
    def __init__(self, member: nextcord.Member, amount: int) -> None:
        if _blackjack_games.get(f'{member.guild.id}:{member.id}'):
            raise TypeError('Game is started')

        _blackjack_games[f'{member.guild.id}:{member.id}'] = self
        self.member = member
        self.amount = amount
        self.cards = CARDS.copy()
        self.your_cards = [self.get_random_cart() for _ in range(2)]
        self.dealer_cards = [self.get_random_cart() for _ in range(2)]
        self.gid = randquan(9)

    @property
    def your_value(self) -> int:
        return self.calculate_result(self.your_cards)

    @property
    def dealer_value(self) -> int:
        return self.calculate_result(self.dealer_cards)

    async def completed_embed(self) -> nextcord.Embed:
        gdb = GuildDateBases(self.member.guild.id)
        color = await gdb.get('color')

        embed = nextcord.Embed(
            title="Blackjack",
            description=f"Result: {await self.get_winner_title()}",
            color=color
        )
        embed.add_field(
            name="Your Hand", value=f"{' '.join(self.your_cards)}\n\nValue: {self.your_value}")
        embed.add_field(
            name="Dealer Hand", value=f"{' '.join(self.dealer_cards)}\n\nValue: {self.dealer_value}")
        return embed

    async def embed(self) -> nextcord.Embed:
        gdb = GuildDateBases(self.member.guild.id)
        color = await gdb.get('color')
        economic_settings = await gdb.get('economic_settings')
        currency_emoji = economic_settings.get('emoji')

        embed = nextcord.Embed(
            title="Blackjack",
            description=f"Bet: {self.amount}{currency_emoji}",
            color=color
        )
        embed.add_field(
            name="Your Hand", value=f"{' '.join(self.your_cards)}\n\nValue: {self.your_value}")
        embed.add_field(
            name="Dealer Hand", value=f"{self.dealer_cards[0]} {Emoji.empty_card}\n\nValue: {self.calculate_result(self.dealer_cards[:1])}")
        return embed

    def is_avid_winner(self) -> Optional[int]:
        if self.your_value == 21 and self.dealer_value == 21 and len(self.your_cards) == 2 and len(self.dealer_cards) == 2:
            return 2
        elif self.your_value == 21 and len(self.your_cards) == 2:
            return 1
        elif self.dealer_value == 21 and len(self.dealer_cards) == 2:
            return 0
        return None

    def is_winner(self) -> int:
        if self.is_exceeds_dealer():
            return 1
        if self.is_exceeds_your():
            return 0
        if self.your_value == self.dealer_value:
            return 2
        return 1 if self.your_value > self.dealer_value else 0

    async def get_winner_title(self) -> str:
        gdb = GuildDateBases(self.member.guild.id)
        economic_settings = await gdb.get('economic_settings')
        currency_emoji = economic_settings.get('emoji')

        match self.is_winner():
            case 2:
                return f"Draw {self.amount:,}{currency_emoji}"
            case 1:
                return f"Won {1.5 * self.amount:,.0f}{currency_emoji}" if self.is_avid_winner() == 1 else f"Won {self.amount:,}{currency_emoji}"
            case 0:
                return f"Loss -{self.amount:,}{currency_emoji}"

    def is_exceeds_your(self) -> bool:
        return self.your_value > 21

    def is_exceeds_dealer(self) -> bool:
        return self.dealer_value > 21

    def go_dealer(self) -> None:
        while True:
            win_cards = []
            for card in self.cards:
                res = self.calculate_result(self.dealer_cards + [card])
                if res <= 21:
                    win_cards.append(card)
            _log.debug('Win cards: %s, Chance: %s', len(
                win_cards), len(win_cards) / len(self.cards))
            if len(win_cards) / len(self.cards) >= 0.4:
                self.add_dealer_card()
            else:
                break

    def add_dealer_card(self) -> None:
        self.dealer_cards.append(self.get_random_cart())

    def add_your_card(self) -> None:
        self.your_cards.append(self.get_random_cart())

    def complete(self) -> None:
        _blackjack_games.pop(f'{self.member.guild.id}:{self.member.id}', None)

    @staticmethod
    def calculate_result(_cards: List[str]) -> int:
        result = 0
        count_of_none = 0
        for val in map(CARDS.__getitem__, _cards):
            if val is None:
                count_of_none += 1
            else:
                result += val
        for _ in range(count_of_none):
            result += 11 if result + 11 <= 21 else 1
        return result

    def get_random_cart(self) -> str:
        val = random.choice(list(self.cards))
        self.cards.pop(val)
        return val
