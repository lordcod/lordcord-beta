from __future__ import annotations


import asyncio
import functools
import logging
import time

from typing import Any, Mapping, Optional, Sequence

import psycopg2
import psycopg2._json
import psycopg2.extras
import psycopg2.extensions
from psycopg2.extras import LoggingConnection, LoggingCursor

from bot.databases.misc.error_handler import on_error
from .misc.adapter_dict import adapt_dict, decode_dict

_lock = asyncio.Lock()
_log = logging.getLogger(__name__)

Vars = Sequence[Any] | Mapping[str, Any] | None

psycopg2.extensions.register_adapter(dict, adapt_dict)
psycopg2.extensions.register_adapter(list, adapt_dict)
psycopg2._json.register_default_json(loads=decode_dict)
psycopg2._json.register_default_jsonb(loads=decode_dict)


class MyLoggingCursor(LoggingCursor):
    def execute(self, query, vars=None):
        self.timestamp = time.time()
        return super(MyLoggingCursor, self).execute(query, vars)

    def callproc(self, procname, vars=None):
        self.timestamp = time.time()
        return super(MyLoggingCursor, self).callproc(procname, vars)


class MyLoggingConnection(LoggingConnection):
    def __init__(
        self,
        dsn: str,
        async_: int = 0,
        debug_logs: bool = False
    ) -> None:
        super().__init__(dsn, async_=async_)
        self.debug_logs = debug_logs

    def filter(self, msg: bytes, curs: MyLoggingCursor):
        return msg.decode() + "   %d ms" % int((time.time() - curs.timestamp) * 1000)

    def cursor(self, *args, **kwargs):
        kwargs.setdefault('cursor_factory', MyLoggingCursor)
        return LoggingConnection.cursor(self, *args, **kwargs)

    def _logtologger(self, msg, curs):
        msg = self.filter(msg, curs)
        if msg and self.debug_logs:
            self._logobj.trace(msg)


def on_lock_complete(func):
    @functools.wraps(func)
    async def wrapped(*args, **kwargs):
        async with _lock:
            return await func(*args, **kwargs)
    return wrapped


class DataBase:
    conn_dns: str
    debug_logs: bool

    def __init__(self) -> None:
        self.__connection: Optional[psycopg2.extensions.connection] = None

    async def get_connection(self):
        if not self.__connection or self.__connection.closed:
            self.__connection = psycopg2.connect(self.conn_dns, connection_factory=MyLoggingConnection)
            self.__connection.debug_logs = self.debug_logs
            self.__connection.autocommit = True
            self.__connection.initialize(_log)
            _log.debug('Database pool connection opened')
        return self.__connection

    @classmethod
    async def create_engine(
        cls,
        dns: str,
        *,
        debug_logs: bool = False
    ) -> DataBase:
        _log.debug("Load DataBases")

        self = cls()
        self.debug_logs = debug_logs
        self.conn_dns = dns

        await self.get_connection()
        return self

    @on_error()
    @on_lock_complete
    async def execute(
        self,
        query: str | bytes,
        vars: Vars = None
    ) -> None:
        vars = vars if vars is not None else []
        conn = await self.get_connection()

        with conn.cursor() as cursor:
            cursor.execute(query, vars)

    @on_error()
    @on_lock_complete
    async def fetchall(
        self,
        query: str | bytes,
        vars: Vars = None
    ) -> list[tuple[Any, ...]]:
        vars = vars if vars is not None else []
        conn = await self.get_connection()

        with conn.cursor() as cursor:
            cursor.execute(query, vars)
            return cursor.fetchall()

    @on_error()
    @on_lock_complete
    async def fetchone(
        self,
        query: str | bytes,
        vars: Vars = None
    ) -> tuple[Any, ...] | None:
        vars = vars if vars is not None else []
        conn = await self.get_connection()

        with conn.cursor() as cursor:
            cursor.execute(query, vars)
            return cursor.fetchone()

    @on_error()
    @on_lock_complete
    async def fetchvalue(
        self,
        query: str | bytes,
        vars: Vars = None
    ) -> Any | None:
        vars = vars if vars is not None else []
        conn = await self.get_connection()

        with conn.cursor() as cursor:
            cursor.execute(query, vars)
            data = cursor.fetchone()

            if data is None:
                return

            return data[0]

    @on_error()
    @on_lock_complete
    async def fetchone_dict(
        self,
        query: str | bytes,
        vars: Vars = None
    ) -> dict:
        vars = vars if vars is not None else []
        conn = await self.get_connection()

        with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
            cursor.execute(query, vars)
            val = cursor.fetchone()
            if val is None:
                return None
            return dict(val)
