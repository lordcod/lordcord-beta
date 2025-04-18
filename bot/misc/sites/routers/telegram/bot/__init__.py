import logging

from aiogram import Dispatcher
from aiogram.types import ErrorEvent

from .commands import start
from .commands import active
from . import messages, settings


dp = Dispatcher()
_log = logging.getLogger(__name__)


@dp.error()
async def error_handler(event: ErrorEvent):
    _log.critical("Critical error caused by %s",
                  event.exception, exc_info=True)

routers = [start.router, active.router, settings.router, messages.router]
dp.include_routers(*routers)
