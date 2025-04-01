
import io
import logging
from logging import _srcfile
import os
import sys
import traceback
import asyncio


log_webhook = os.environ.get('log_webhook')
loop = asyncio.get_event_loop()

TRACE = logging.DEBUG - 5
CORE = logging.INFO + 5

DEFAULT_LOG = TRACE
DEFAULT_DISCORD_LOG = logging.INFO
DEFAULT_FILE_LOG = logging.ERROR

DEFAULT_HTTP_LOGS = (
    'bot'
)
DEFAULT_LOGS = {
    'nextcord': logging.INFO,
    'pyngrok': logging.NOTSET,
    'git': logging.INFO,
    'httpx': logging.INFO,
    'aiocache': logging.ERROR,
    'colormath': logging.INFO,
    'aiosqlite': logging.INFO,
    'tortoise': logging.INFO,
    'uvicorn': logging.INFO,
}

BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE = range(8)

RESET_SEQ = "\033[0m"
COLOR_SEQ = "\033[1;%dm"
BOLD_SEQ = "\033[1m"

RESET_SEQD = '[0m'
COLOR_SEQD = '[2;%dm'
BOLD_SEQD = '[2;1m'

COLORS = {
    'WARNING': YELLOW,
    'INFO': GREEN,
    'DEBUG': BLUE,
    'CRITICAL': YELLOW,
    'ERROR': RED,
    'TRACE': CYAN,
    'CORE': MAGENTA
}

task_lock = asyncio.Lock()


def currentframe(): return sys._getframe(3)


def _is_internal_frame(frame):
    """Signal whether the frame is a CPython or logging module internal."""
    filename = os.path.normcase(frame.f_code.co_filename)
    return filename == _srcfile or (
        "importlib" in filename and "_bootstrap" in filename
    )


def formatter_message(message, use_color=True):
    if use_color:
        message = message.replace(
            "$RESET", RESET_SEQ).replace("$BOLD", BOLD_SEQ)
    else:
        message = message.replace("$RESET", "").replace("$BOLD", "")
    return message


def formatter_discord_message(message, use_color=True):
    if use_color:
        message = message.replace(
            "$RESET", RESET_SEQD).replace("$BOLD", BOLD_SEQD)
    else:
        message = message.replace("$RESET", "").replace("$BOLD", "")
    return message


async def post_mes(webhook_url: str, text: str) -> None:
    from bot.main import bot
    _log = logging.getLogger('beta.bot.misc.webhook')

    async with task_lock:
        data = {
            'content': '```ansi\n' + text[:1900] + '```'
        }
        async with bot.session.post(webhook_url, data=data) as response:
            if response.ok:
                return

            try:
                response.raise_for_status()
            except Exception:
                _log.exception('Error send webhook message: %s',
                               await response.json())

            if response.status == 429:
                seconds = int(response.headers.get(
                    'X-RateLimit-Reset-After', 0))
                logging.warning(
                    'Sending the log was delayed for %d seconds', seconds)
                await asyncio.sleep(seconds)
                post_mes(webhook_url, text)


class StandartFormatter(logging.Formatter):
    """override logging.Formatter to use an aware datetime object"""


class DiscordColoredFormatter(StandartFormatter):
    def __init__(self, msg, use_color=True):
        logging.Formatter.__init__(self, msg, datefmt='%m-%d-%Y %H:%M:%S')
        self.use_color = use_color

    def format(self, record):
        levelname = record.levelname
        if self.use_color and levelname in COLORS:
            levelname_color = COLOR_SEQD % (
                30 + COLORS[levelname]) + levelname + RESET_SEQD
            record.levelname = levelname_color
        return logging.Formatter.format(self, record)


class ColoredFormatter(StandartFormatter):
    def __init__(self, msg, use_color=True):
        logging.Formatter.__init__(self, msg, datefmt='%m-%d-%Y %H:%M:%S')
        self.use_color = use_color

    def format(self, record):
        levelname = record.levelname
        if self.use_color and levelname in COLORS:
            levelname_color = COLOR_SEQ % (
                30 + COLORS[levelname]) + levelname + RESET_SEQ
            record.levelname = levelname_color
        return logging.Formatter.format(self, record)


class DiscordHandler(logging.Handler):
    def __init__(self, webhook_url: str) -> None:
        self.webhook_url = webhook_url
        self.posters_tasks = []
        super().__init__()

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            task = loop.create_task(post_mes(self.webhook_url, msg))
            self.posters_tasks.append(task)
            self.flush()
        except RecursionError:
            raise
        except Exception:
            self.handleError(record)


class LordLogger(logging.Logger):
    FORMAT = "[$BOLD%(asctime)s$RESET][$BOLD%(name)s$RESET][%(levelname)s]  %(message)s ($BOLD%(filename)s$RESET:%(lineno)d)"
    COLOR_FORMAT = formatter_message(FORMAT, True)
    NO_COLOR_FORMAT = formatter_message(FORMAT, False)

    def __init__(self, name: str, level: int = DEFAULT_LOG):
        for dfl_log, dfl_level in DEFAULT_LOGS.items():
            if name.startswith(dfl_log):
                level = dfl_level

        logging.Logger.__init__(self, name, level)
        [self.removeHandler(hand) for hand in self.handlers]

        color_formatter = ColoredFormatter(self.COLOR_FORMAT)
        self.console = logging.StreamHandler()
        self.console.setFormatter(color_formatter)
        self.addHandler(self.console)

        color_formatter = DiscordColoredFormatter(self.COLOR_FORMAT)
        self.discord_handler = DiscordHandler(log_webhook)
        self.discord_handler.setFormatter(color_formatter)
        self.discord_handler.setLevel(DEFAULT_DISCORD_LOG)
        if name.startswith(DEFAULT_HTTP_LOGS):
            self.addHandler(self.discord_handler)

    def _findCaller(self, stack_info=False, stacklevel=1):
        """
        Find the stack frame of the caller so that we can note the source
        file name, line number and function name.
        """
        # On some versions of IronPython, currentframe() returns None if
        # IronPython isn't run with -X:Frames.
        f = currentframe()
        if f is None:
            return "(unknown file)", 0, "(unknown function)", None
        while stacklevel > 0:
            next_f = f.f_back
            if next_f is None:
                break
            f = next_f
            if not _is_internal_frame(f):
                stacklevel -= 1
        co = f.f_code
        sinfo = None
        if stack_info:
            with io.StringIO() as sio:
                sio.write("Stack (most recent call last):\n")
                traceback.print_stack(f, file=sio)
                sinfo = sio.getvalue()
                if sinfo[-1] == '\n':
                    sinfo = sinfo[:-1]
        return co.co_filename, f.f_lineno, co.co_name, sinfo

    def _adt_log(self, level, msg, *args, exc_info=None, extra=None, stack_info=False,
                 stacklevel=1):
        """
        Low-level logging routine which creates a LogRecord and then calls
        all the handlers of this logger to handle the record.
        """
        sinfo = None
        if _srcfile:
            # IronPython doesn't track Python frames, so findCaller raises an
            # exception on some versions of IronPython. We trap it here so that
            # IronPython can use logging.
            try:
                fn, lno, func, sinfo = self._findCaller(stack_info, stacklevel)
            except ValueError:  # pragma: no cover
                fn, lno, func = "(unknown file)", 0, "(unknown function)"
        else:  # pragma: no cover
            fn, lno, func = "(unknown file)", 0, "(unknown function)"
        if exc_info:
            if isinstance(exc_info, BaseException):
                exc_info = (type(exc_info), exc_info, exc_info.__traceback__)
            elif not isinstance(exc_info, tuple):
                exc_info = sys.exc_info()
        record = self.makeRecord(self.name, level, fn, lno, msg, args,
                                 exc_info, func, extra, sinfo)
        self.handle(record)

    def trace(self, msg, *args, **kwargs):
        """
        Log 'msg % args' with severity 'TRACE'.

        To pass exception information, use the keyword argument exc_info with
        a true value, e.g.

        logger.trace("Houston, we have a %s", "interesting problem", exc_info=1)
        """
        self.debug
        if self.isEnabledFor(TRACE):
            self._adt_log(TRACE, msg, *args, **kwargs)

    def core(self, msg, *args, **kwargs):
        """
        Log 'msg % args' with severity 'CORE'.

        To pass exception information, use the keyword argument exc_info with
        a true value, e.g.

        logger.core("Houston, we have a %s", "interesting problem", exc_info=1)
        """

        if self.isEnabledFor(CORE):
            self._adt_log(CORE, msg, *args, **kwargs)


logging.setLoggerClass(LordLogger)

logging.addLevelName(TRACE, 'TRACE')
logging.addLevelName(CORE, 'CORE')
