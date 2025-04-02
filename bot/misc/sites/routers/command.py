from __future__ import annotations
import contextlib
from typing import TYPE_CHECKING
from fastapi import APIRouter, Request
from bot.languages import i18n
from bot.languages.help import commands

if TYPE_CHECKING:
    from bot.misc.lordbot import LordBot


def parse_command(locale: str, cmd: dict):
    data = cmd.copy()

    name = data.get('name')
    count_args = data.pop('count_args', 0)
    count_examples = data.pop('count_examples', 0)

    data['description'] = i18n.t(locale,
                                 f"commands.command.{name}.description")
    data['brief'] = i18n.t(locale, f"commands.command.{name}.brief")

    for i in range(count_examples):
        use = i18n.t(
            locale, f'commands.command.{name}.examples.{i}.use')
        desc = i18n.t(
            locale, f'commands.command.{name}.examples.{i}.desc')
        data.setdefault('examples', [])
        data['examples'].append({'use': use, 'desc': desc})

    for i in range(count_args):
        arg = i18n.t(locale, f'commands.command.{name}.arguments.{i}')
        data.setdefault('arguments', [])
        data['arguments'].append(arg)

    return data


class CommandRouter:
    def __init__(
        self,
        bot: LordBot
    ) -> None:
        self.bot = bot

    def _setup(self, prefix: str = "") -> APIRouter:
        router = APIRouter(prefix=prefix)

        router.add_api_route(
            '/',
            self._get,
            methods=['GET']
        )

        return router

    def _get(self, request: Request, locale: str):
        answer = []
        for cmd in commands:
            with contextlib.suppress(Exception):
                answer.append(parse_command(locale, cmd))

        return answer
