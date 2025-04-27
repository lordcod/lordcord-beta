import asyncio
from datetime import datetime
import logging
import random
import time
from PIL import Image, ImageFont
import io
import nextcord
from aiohttp import ClientSession
from bot.misc.utils.image_utils import WelcomeImageGenerator
from unittest.mock import MagicMock

# Настройка логирования
logging.basicConfig(level=logging.DEBUG)
_log = logging.getLogger(__name__)


class State():
    def _get_client(self):
        return member

    def __str__(self):
        return '<State>'

    def __getattribute__(self, name):
        if name == 'mention':
            return "<Sate>"
        if name == 'url':
            return None
        return State()


class FakeMember(nextcord.Member):
    def __init__(self, guild, user_id: int, username: str, discriminator: str):
        self._user = nextcord.User(state=State(), data={
            'id': user_id,
            'username': username,
            'discriminator': discriminator,
            'avatar': None,
            'bot': False
        })
        self.guild = guild  # Гильдия, в которой состоит пользователь
        self._avatar = None
        self._state = State()
        self.nick = None


class FakeGuild:
    def __init__(self, guild_id: int, guild_name: str, member_count: int, premium_count: int):
        self.id = guild_id
        self.name = guild_name
        self.member_count = member_count
        self.premium_subscription_count = premium_count
        self.icon = None  # Пример иконки
        self.created_at = datetime.now()
        self._state = State()


guild = FakeGuild(
    guild_id=random.randint(1000000000, 9999999999),
    guild_name="Test Server",
    member_count=random.randint(1, 1000),
    premium_count=random.randint(0, 10)
)

member = FakeMember(
    guild=guild,
    user_id=random.randint(1000000000, 9999999999),
    username="user123",
    discriminator="1234"
)


def create_test_config():
    return {
        "background": {
            "width": 800,
            "height": 450,
            "url": "assets/background.jpg"
        },
        "images": [{
            "type": "avatar",
            "target": "member",
            "size": [140, 140],
            "position": [330, 100],
            "border": {
                    "color": "#ff00ff",
                    "width": 15,
                    "radius": 70
            }
        }],
        "texts": [{
            "type": "gradient",
            "text": "HELLO, { member.username?&upper }",
            "font_path": "assets/Nunito-ExtraBold.ttf",
            "font_size": 38,
            "x": 400,
            "y": 260,
            "color_start": [100, 150, 255],
            "color_stop": [200, 220, 255],
            "max_width": 680
        }, {
            "type": "simple",
            "text": "{ guild.name }",
            "font_path": "assets/Nunito-ExtraBold.ttf",
            "font_size": 28,
            "x": 400,
            "y": 315,
            "fill": "#E0E0E0"
        }, {
            "type": "simple",
            "text": "Member #{ guild.memberCount }",
            "font_path": "assets/Nunito-ExtraBold.ttf",
            "font_size": 23,
            "x": 400,
            "y": 355,
            "fill": "#A0A0A0"
        }]
    }


async def main():
    # Мокируем необходимые объекты
    session = ClientSession()
    config = create_test_config()

    generator = WelcomeImageGenerator(member, session, config)

    output = await generator.generate()

    output.seek(0)
    img = Image.open(output)
    img.show()


async def run():
    await main()
    input()

if __name__ == "__main__":
    asyncio.run(run())
