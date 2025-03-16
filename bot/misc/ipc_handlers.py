from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from bot.languages.help import commands
from bot.languages import i18n


if TYPE_CHECKING:
    from bot.misc.lordbot import LordBot


handlers = {}


def ipc_route(name: Optional[str] = None, ratelimit: Optional[int] = None):
    def wrapped(func):
        _name = name or func.__name__
        func.__limit__ = ratelimit
        handlers[_name] = func
        return func
    return wrapped


@ipc_route(ratelimit=60)
async def get_guilds_count(bot: LordBot, _: dict):
    return {
        'guilds_count': len(bot.guilds)
    }


@ipc_route(ratelimit=60)
async def get_members_count(bot: LordBot, _: dict):
    return {
        'members_count': len(list(bot.get_all_members()))
    }


@ipc_route(ratelimit=10)
async def get_command_data(bot: LordBot, _: dict):
    new_commands = []
    for cmd in commands:
        cmd_name = cmd.get('name')

        data = dict(cmd)
        data['examples'] = []
        data['description'] = i18n.get_dict(f"commands.command.{cmd_name}.description")
        data['brief_description'] = i18n.get_dict(f"commands.command.{cmd_name}.brief")
        data['arguments'] = []

        for i in range(data.pop('count_args')):
            data['arguments'].append(i18n.get_dict(f"commands.command.{cmd_name}.arguments.{i}"))
        for i in range(data.pop('count_examples')):
            try:
                data['examples'].append([
                    i18n.t(path=f"commands.command.{cmd_name}.examples.{i}.use"),
                    i18n.get_dict(f"commands.command.{cmd_name}.examples.{i}.desc")
                ])
            except ValueError:
                pass
        new_commands.append(data)
    return new_commands
