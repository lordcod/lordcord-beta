import contextlib
from enum import StrEnum
import orjson
from typing import Any,  Union, overload, TypeVar
import psycopg2
from psycopg2._psycopg import ISQLQuote, QuotedString
import psycopg2._psycopg

from bot.databases.misc.error_handler import on_error

T = TypeVar('T')


class NumberFormatType(StrEnum):
    FLOAT = 'FLOAT'
    INT = 'INTEGER'


class QuotedJson():
    def __init__(self, adapted):
        self.adapted = adapted
        self._conn = None

    def __conform__(self, proto):
        if proto is ISQLQuote:
            return self

    def prepare(self, conn):
        self._conn = conn

    def getquoted(self):
        s = self.adapted
        qs = QuotedString(s)
        if self._conn is not None:
            qs.prepare(self._conn)
        try:
            return qs.getquoted()
        except Exception:
            pass

    def __str__(self):
        return self.getquoted().decode('ascii', 'replace')


class FullJson:
    def __init__(self, overnumber: bool = False) -> None:
        self.overnumber = overnumber
        self.encoding = 'utf-8'

    @overload
    def loads(self, data: Union[bytes, bytearray, memoryview, str]) -> dict:
        pass

    @overload
    def loads(self, data: T) -> T:
        pass

    @overload
    @staticmethod
    def loads(data: Union[bytes, bytearray, memoryview, str]) -> dict:
        pass

    @overload
    @staticmethod
    def loads(data: T) -> T:
        pass

    def loads(*args):
        if len(args) == 1:
            dict_var = args[0]
            overnumber = False
        elif len(args) == 2:
            self = args[0]
            dict_var = args[1]
            overnumber = self.overnumber

        data = Json.loads(dict_var)
        data = NumberFormating.loads(data, overnumber)
        return data

    @staticmethod
    def dumps(dict_var):
        data = NumberFormating.dumps(dict_var)
        data = Json.dumps(data)
        return data


class Json:
    @staticmethod
    def loads(data) -> dict:
        if not isinstance(data, (bytes, bytearray, memoryview, str)):
            return data
        try:
            return orjson.loads(data)
        except orjson.JSONDecodeError:
            return data

    @staticmethod
    def dumps(data):
        try:
            return orjson.dumps(data).decode()
        except orjson.JSONEncodeError:
            return data


class NumberFormating:
    @staticmethod
    def encode_number(number: Union[int, float, str]) -> str:
        if isinstance(number, float):
            return f"__CONVERT_NUMBER__ FLOAT {number}"
        elif isinstance(number, int):
            return f"__CONVERT_NUMBER__ INTEGER {number}"
        return number

    @staticmethod
    def decode_number(value: str, over: bool) -> Union[int, float, str]:
        if isinstance(value, str) and over:
            with contextlib.suppress(BaseException):
                return int(value)
            with contextlib.suppress(BaseException):
                return float(value)
        if not (isinstance(value, str) and
                value.startswith("__CONVERT_NUMBER__ ")):
            return value
        numtype = value.split()[1]

        if numtype == NumberFormatType.FLOAT:
            return float(value.removeprefix("__CONVERT_NUMBER__ FLOAT "))
        elif numtype == NumberFormatType.INT:
            return int(value.removeprefix("__CONVERT_NUMBER__ INTEGER "))
        else:
            try:
                return int(value.removeprefix("__CONVERT_NUMBER__ "))
            except ValueError:
                return value

    @staticmethod
    @on_error()
    def loads(data: Any, over: bool = False):
        if not isinstance(data, dict):
            return data
        new_data = {}
        for key, value in data.items():
            new_data[NumberFormating.decode_number(
                key, over)] = NumberFormating.loads(value, over)
        return new_data

    @staticmethod
    @on_error()
    def dumps(data: Any):
        if not isinstance(data, dict):
            return data
        new_data = {}
        for key, value in data.items():
            new_data[NumberFormating.encode_number(
                key)] = NumberFormating.dumps(value)
        return new_data


def adapt_dict(dict_var):
    data = NumberFormating.dumps(dict_var)
    data = Json.dumps(data)
    qj = QuotedJson(data)
    return qj


def decode_dict(dict_var):
    data = Json.loads(dict_var)
    data = NumberFormating.loads(data)
    return data


def adapt_array(list_var):
    data = psycopg2._psycopg.List(list_var)
    return data
