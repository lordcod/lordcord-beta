# bot/misc/time_calculator.py
import time
import re
import contextlib
from datetime import datetime
from typing import Any, T, Optional
from nextcord.ext import commands


class TimeCalculator:
    def __init__(
        self,
        default_coefficient: int = 60,
        refundable: T = int,
        coefficients: Optional[dict] = None,
        operatable_time: bool = False,
        errorable: bool = True
    ) -> None:
        self.default_coefficient = default_coefficient
        self.refundable = refundable
        self.operatable_time = operatable_time
        self.errorable = errorable
        self.coefficients = coefficients or {
            's': 1, 'm': 60, 'h': 3600, 'd': 86400}

    def convert(self, *args) -> T:
        try:
            return self.async_convert(*args)
        except Exception:
            pass
        try:
            return self.basic_convert(*args)
        except Exception:
            pass
        if self.errorable:
            raise TypeError
        return None

    def basic_convert(self, argument: Any) -> T:
        try:
            return int(argument)
        except ValueError:
            pass
        if not isinstance(argument, str) or not re.fullmatch(r'\s*(\d+[a-zA-Z\s]+){1,}', argument):
            raise TypeError('Format time is not valid!')
        timedate = re.findall(r'(\d+)([a-zA-Z\s]+)', argument)
        ftime = sum(int(n) * self.coefficients[w.strip()]
                    for n, w in timedate if w.strip() in self.coefficients)
        if not ftime:
            raise TypeError('Format time is not valid!')
        return self.refundable(ftime + time.time()) if self.operatable_time else self.refundable(ftime)

    async def async_convert(self, ctx: commands.Context, argument: Any) -> T:
        return self.basic_convert(argument)


def translate_to_timestamp(arg: str) -> int | None:
    formats = [
        '%H:%M', '%H:%M:%S', '%d.%m.%Y', '%d.%m.%Y %H:%M', '%d.%m.%Y %H:%M:%S',
        '%H:%M %d.%m.%Y', '%H:%M:%S %d.%m.%Y', '%Y-%m-%d', '%H:%M %Y-%m-%d',
        '%H:%M:%S %Y-%m-%d', '%Y-%m-%d %H:%M', '%Y-%m-%d %H:%M:%S'
    ]
    for fmt in formats:
        with contextlib.suppress(ValueError):
            dt = datetime.strptime(arg, fmt)
            if dt.year == 1900:
                now = datetime.today()
                dt = dt.replace(year=now.year, month=now.month, day=now.day)
            return int(dt.timestamp())

    with contextlib.suppress(TypeError):
        return TimeCalculator(operatable_time=True).convert(arg)
    return None
