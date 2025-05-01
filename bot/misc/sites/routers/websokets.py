from __future__ import annotations
import asyncio
from collections import defaultdict
import logging
import time
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

if TYPE_CHECKING:
    from bot.misc.lordbot import LordBot

_log = logging.getLogger(__name__)


class WaitWebSocket:
    def __init__(self):
        loop = asyncio.get_event_loop()
        self.future = loop.create_future()

    async def send_json(self, data: Any):
        if self.future.cancelled():
            return

        try:
            self.future.set_result(data)
        except asyncio.InvalidStateError:
            pass


class WebSocketRouter():
    bot: LordBot
    websockets: Dict[str, List[Tuple[WebSocket, int, float]]]

    def __init__(
        self,
        bot: LordBot
    ) -> None:
        bot._set_callback_api_state(self.send_api_state, self.wait_api_state)

        self.bot = bot
        self.websockets = defaultdict(list)

    async def wait_api_state(self, state: str,
                             *, timeout: Optional[int] = None):
        ws = WaitWebSocket()
        self.websockets[state].append(ws)

        return await asyncio.wait_for(ws.future, timeout)

    async def send_api_state(self, state: str, data: Any):
        websockets = self.websockets[state]
        time_now = time.time()
        for index, data in enumerate(websockets.copy()):
            ws, count, time_created = data
            if time_created+3600 > time_now:
                websockets.remove(data)
                continue
            if count <= 0:
                websockets.remove(data)
                continue

            try:
                await ws.send_json({
                    't': 'RECEIVE_STATE',
                    's': state,
                    'd': data
                })
            except (WebSocketDisconnect, KeyError, RuntimeError):
                websockets.remove(data)
            else:
                websockets[index] = (ws, count-1)
        return True

    def _setup(self, prefix: str = ''):
        router = APIRouter(prefix=prefix)

        router.add_api_websocket_route('/ws', self._websocket_endpoint)

        return router

    async def _websocket_endpoint(self, websocket: WebSocket):
        await websocket.accept()
        while True:
            try:
                data = await websocket.receive_json()
            except WebSocketDisconnect:
                break

            if data['t'] == 'WAIT_STATE':
                self.websockets[data['d']['state']].append(websocket)
            if data['t'] == 'SEND_STATE':
                state = data['d']['state']
                await self.send_api_state(state, data['d']['result'])
