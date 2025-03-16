
from asyncio import iscoroutine
import functools
import logging
from typing import Any, Callable


_log = logging.getLogger(__name__)


def on_error():
    def wrapped(func: Callable) -> Any:
        @functools.wraps(func)
        def inner(*args, **kwargs):
            for i in range(3):
                try:
                    return func(*args, **kwargs)
                except BaseException as exc:
                    _log.error(f"[ON_ERROR][{func.__name__}][{exc.__class__.__name__}]: Attempt: {i+1}/3, {args}", exc_info=exc)
        return inner
    return wrapped
