import logging
import logging.config
import asyncio
import orjson

from bot.misc.env import Tokens

TRACE = logging.DEBUG - 5
CORE = logging.INFO + 5

COLORS = {
    'WARNING': 33,
    'INFO': 32,
    'DEBUG': 34,
    'CRITICAL': 35,
    'ERROR': 31,
    'TRACE': 36,
    'CORE': 35
}

RESET_SEQ = "\033[0m"
COLOR_SEQ = "\033[1;%dm"


def colorize(level, text):
    color = COLORS.get(level, 37)
    return COLOR_SEQ % color + text + RESET_SEQ


class ColoredFormatter(logging.Formatter):
    def format(self, record):
        record.levelname = colorize(record.levelname, record.levelname)
        return super().format(record)


task_lock = asyncio.Lock()


async def post_mes(webhook_url: str, text: str):
    from bot.main import bot
    logger = logging.getLogger("discord.webhook")
    async with task_lock:
        data = {"content": f"```ansi\n{text[:1900]}```"}
        async with bot.session.post(webhook_url, data=data) as response:
            if not response.ok:
                try:
                    response.raise_for_status()
                except Exception:
                    logger.exception("Error posting to webhook: %s", await response.text())

                if response.status == 429:
                    retry = int(response.headers.get(
                        "X-RateLimit-Reset-After", 0))
                    await asyncio.sleep(retry)
                    await post_mes(webhook_url, text)


class DiscordHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.webhook_url = Tokens.log_webhook
        self.loop = asyncio.get_event_loop()

    def emit(self, record):
        try:
            msg = self.format(record)
            self.loop.create_task(post_mes(self.webhook_url, msg))
        except Exception:
            self.handleError(record)


class LordLogger(logging.Logger):
    def __init__(self, name: str, level: int = logging.NOTSET):
        super().__init__(name, level)

    def trace(self, msg, *args, **kwargs):
        if self.isEnabledFor(TRACE):
            self._log(TRACE, msg, args, **kwargs)

    def core(self, msg, *args, **kwargs):
        if self.isEnabledFor(CORE):
            self._log(CORE, msg, args, **kwargs)


def setup_logging(config_path="assets/log_config.json"):
    with open(config_path, "rb") as f:
        config = orjson.loads(f.read())

    logging.setLoggerClass(LordLogger)
    logging.addLevelName(TRACE, "TRACE")
    logging.addLevelName(CORE, "CORE")
    logging.config.dictConfig(config)
