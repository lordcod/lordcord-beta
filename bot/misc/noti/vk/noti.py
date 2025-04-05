import asyncio
import time

import nextcord
from bot.misc.noti.base import Notification


class VkNoti(Notification[None]):
    def __init__(self, bot, heartbeat_timeout=180):
        super().__init__(bot, None, heartbeat_timeout)

    async def callback(self, data: dict):
        pass

    async def parse(self):
        if self.running:
            return

        self._running = True

        self.bot.add_listener(self.callback, 'on_vk_post')

        while True:
            await asyncio.sleep(self.heartbeat_timeout)
            if not self._running:
                break

            self.last_heartbeat = time.time()
