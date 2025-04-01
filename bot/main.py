import asyncio
import nextcord
from bot.misc import env
from bot.misc.lordbot import LordBot

import os

from bot.misc.utils import get_parser_args


bot = LordBot(
    loop=asyncio.get_event_loop(),
    chunk_guilds_at_startup=False
)


def load_dir(dirpath: str) -> None:
    for filename in os.listdir(dirpath):
        if (os.path.isfile(f'{dirpath}/{filename}')
                and filename.endswith(".py")):
            fmp = filename[:-3]
            supath = dirpath[2:].replace("/", ".")

            bot.load_extension(f"{supath}.{fmp}")
        elif os.path.isdir(f'{dirpath}/{filename}'):
            load_dir(f'{dirpath}/{filename}')


def start_bot():
    flags = get_parser_args()

    load_dir("./bot/cogs")

    try:
        if token_name := flags.get('token'):
            token = getattr(env.Tokens, 'token_'+token_name)
        else:
            token = env.Tokens.token
        bot.run(token)
    except nextcord.HTTPException:
        return
