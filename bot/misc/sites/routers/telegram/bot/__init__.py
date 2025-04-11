from os import getenv

from aiogram import Dispatcher
from . import commands, messages


dp = Dispatcher()

routers = [commands.router, messages.router]
dp.include_routers(*routers)
