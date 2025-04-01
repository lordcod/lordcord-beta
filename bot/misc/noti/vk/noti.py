from bot.misc.noti.base import Notification, NotificationApi


class VkNotiApi(NotificationApi):
    def __init__(self, bot):
        super().__init__(bot)


class VkNoti(Notification[VkNotiApi]):
    def __init__(self, bot, api, heartbeat_timeout=180):
        super().__init__(bot, api, heartbeat_timeout)

    async def callback(self, )

    async def parse(self):
        pass
