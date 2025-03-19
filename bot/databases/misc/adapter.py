import contextlib
from enum import StrEnum
import orjson
from typing import Any,  Union, TypeVar

T = TypeVar('T')


class NumberFormatType(StrEnum):
    FLOAT = 'FLOAT'
    INT = 'INTEGER'


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
    def loads(data: Any, over: bool = False):
        if not isinstance(data, dict):
            return data
        new_data = {}
        for key, value in data.items():
            new_data[NumberFormating.decode_number(
                key, over)] = NumberFormating.loads(value, over)
        return new_data

    @staticmethod
    def dumps(data: Any):
        if not isinstance(data, dict):
            return data
        new_data = {}
        for key, value in data.items():
            new_data[NumberFormating.encode_number(
                key)] = NumberFormating.dumps(value)
        return new_data


def dumps(dict_var, ignore: bool = False):
    try:
        data = NumberFormating.dumps(dict_var)
        data = orjson.dumps(data).decode()
        return data
    except Exception:
        if ignore:
            return dict_var
        raise


def loads(dict_var, ignore: bool = False):
    try:
        data = orjson.loads(dict_var)
        data = NumberFormating.loads(data)
        return data
    except Exception:
        if ignore:
            return dict_var
        raise
