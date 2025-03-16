import time
import nextcord

import enum
from typing import Dict, Optional, TypedDict


class BucketConfig(TypedDict):
    rate: int
    per: float


class GuildBucketConfig(BucketConfig, total=True):
    type: int


data: Dict[str, Dict[str, BucketConfig]] = {}


class BucketType(enum.IntEnum):
    MEMBER = 0
    SERVER = 1


class Cooldown:
    def __init__(
        self,
        command_name: str,
        command_data: GuildBucketConfig,
        token: str
    ) -> None:
        self.command_name = command_name
        self.command_data = command_data
        self.token = token

        self.check_register()

    def check_register(self) -> None:
        data.setdefault(self.command_name, {})
        data[self.command_name].setdefault(self.token, {})

    def get(self) -> Optional[float]:
        cooldata = data[self.command_name][self.token]

        regular_rate: int = self.command_data.get('rate')
        rate: int = cooldata.get('rate', 0)
        per: float = cooldata.get('per', 0)

        if time.time() >= per:
            self.reset()
            return None

        if regular_rate > rate:
            return None

        return round(per-time.time(), 2)

    def add(self) -> None:
        global data

        cooldata = data[self.command_name][self.token]
        rate = cooldata.get('rate', 0)
        per = cooldata.get('per', 0)

        regular_per: int = self.command_data.get('per')

        datatime = time.time()+regular_per if rate == 0 else per

        data[self.command_name][self.token] = {
            'rate': rate+1,
            'per': datatime
        }

    def take(self) -> None:
        global data

        cooldata: dict = data[self.command_name][self.token]
        rate: int = cooldata.get('rate', 0)
        per: float = cooldata.get('per', 0)

        datarate = (0 if 0 >= rate-1
                    else rate-1)

        data[self.command_name][self.token] = {
            'rate': datarate,
            'per': per
        }

    def reset(self) -> None:
        data[self.command_name][self.token] = {
            'rate': 0,
            'per': 0
        }

    @classmethod
    def from_message(
        cls,
        command_name: str,
        command_data: GuildBucketConfig,
        message: nextcord.Message
    ) -> 'Cooldown':
        cooldata = command_data
        cooltype = cooldata.get('type')

        if cooltype == BucketType.MEMBER:
            token = f'{message.guild.id}:{message.author.id}'
        elif cooltype == BucketType.SERVER:
            token = str(message.guild.id)
        else:
            raise ValueError("cooltype %s was not found" % cooltype)

        return Cooldown(
            command_name,
            command_data,
            token
        )
