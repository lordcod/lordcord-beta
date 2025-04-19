import asyncio
import logging
from typing import Coroutine, Dict, Optional, Union
from asyncio import TimerHandle
from dataclasses import dataclass, field

_log = logging.getLogger(__name__)


class LordTimerHandler:
    def __init__(self, loop: asyncio.AbstractEventLoop) -> None:
        self.loop = loop
        self.data: Dict[Union[str, int], TimerHandle] = {}

    def create_timer_handler(
        self,
        delay: float,
        coro: Coroutine,
        key: Optional[Union[str, int]] = None
    ):
        th = self.loop.call_later(delay, self.loop.create_task, coro)
        if key is not None:
            _log.debug(f"Create new timer handle {coro.__name__} (ID:{key})")
            self.data[key] = th

    def close_as_key(self, key: Union[str, int]):
        th = self.data.get(key)
        if th is None:
            return
        arg = th._args[0]
        if asyncio.iscoroutine(arg):
            arg.close()
        th.cancel()

    def close_as_th(self, th: TimerHandle):
        arg = th._args and th._args[0]
        if asyncio.iscoroutine(arg):
            arg.close()
        th.cancel()


@dataclass
class ItemLordTimeHandler:
    delay: Union[int, float]
    coro: Coroutine
    key: Union[str, int]
    th: TimerHandle = field(init=False)


class LordTimeHandler:
    __instance = None

    def __new__(cls, loop: Optional[asyncio.AbstractEventLoop] = None) -> None:
        if cls.__instance is None:
            cls.__instance = object.__new__(cls)
        return cls.__instance

    def __init__(self, loop: Optional[asyncio.AbstractEventLoop] = None) -> None:
        self.loop = loop
        self.data: Dict[Union[str, int], ItemLordTimeHandler] = {}

    def create(self, delay: float, coro: Coroutine, key: Union[str, int]) -> ItemLordTimeHandler:
        _log.debug('Create new temp task %s (%s)', coro.__name__, key)
        ilth = ItemLordTimeHandler(delay, coro, key)
        th = self.loop.call_later(delay, self.complete, ilth)
        ilth.th = th
        self.data[key] = ilth
        return ilth

    def complete(self, ilth: ItemLordTimeHandler) -> None:
        _log.debug('Complete temp task %s (%s)', ilth.coro.__name__, ilth.key)
        self.loop.create_task(ilth.coro, name=ilth.key)
        self.data.pop(ilth.key, None)

    def close(self, key: Union[str, int]) -> Optional[ItemLordTimeHandler]:
        ilth = self.data.pop(key, None)
        if ilth is None:
            return
        ilth.coro.close()
        ilth.th.cancel()
        return ilth

    def call(self, key: Union[str, int]) -> None:
        ilth = self.get(key)
        if ilth is None:
            return
        ilth.th._run()
        self.close(key)

    def increment(self, delay: Union[float, int], key: Union[str, int]) -> None:
        ilth = self.close(key)
        if ilth is None:
            return
        ilth.delay = delay
        th = self.loop.call_later(delay, self.complete, ilth)
        ilth.th = th
        self.data[key] = ilth

    def get(self, key: Union[str, int]) -> Optional[ItemLordTimeHandler]:
        return self.data.get(key)
