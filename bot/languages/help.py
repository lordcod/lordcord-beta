from collections import defaultdict
from typing import List, Dict, Tuple, TypedDict, Union, NotRequired
import jmespath
import orjson
import os


class CommandOption(TypedDict):
    name: str
    category: str
    aliases: List[str]
    allowed_disabled: bool
    count_args: int
    count_examples: int


class ReactionOption(TypedDict):
    name: str
    description: str
    with_user: str


class CommandsPayload(TypedDict):
    categories_emoji: Dict[str, str]
    commands: List[CommandOption]


categories_emoji: Dict[str, str]
categories: Dict[str, List[CommandOption]]
commands: List[CommandOption]

reactions_command = ['airkiss', 'angrystare', 'bite', 'bleh', 'blush', 'brofist', 'celebrate', 'cheers', 'clap', 'confused', 'cool', 'cry', 'cuddle', 'dance', 'drool', 'evillaugh', 'facepalm', 'handhold', 'happy', 'headbang', 'hug', 'kiss', 'laugh', 'lick', 'love', 'mad', 'nervous', 'no', 'nom', 'nosebleed', 'nuzzle',
                     'nyah', 'pat', 'peek', 'pinch', 'poke', 'pout', 'punch', 'roll', 'run', 'sad', 'scared', 'shout', 'shrug', 'shy', 'sigh', 'sip', 'slap', 'sleep', 'slowclap', 'smack', 'smile', 'smug', 'sneeze', 'sorry', 'stare', 'surprised', 'sweat', 'thumbsup', 'tickle', 'tired', 'wave', 'wink', 'woah', 'yawn', 'yay', 'yes']


def get_command(name: str, with_reactions: bool = False) -> CommandOption:
    if not with_reactions and name in reactions_command:
        name = 'reactions'
    expression = f"[?name == '{name}'||contains(aliases, '{name}')]|[0]"
    result = jmespath.search(expression, commands)
    if result is not None:
        return CommandOption(result)


with open("bot/languages/commands_data.json", "rb") as file:
    content = file.read()
    _commands: CommandsPayload = orjson.loads(content)
    categories_emoji = _commands["categories_emoji"]
    commands = _commands["commands"]

    categories = {}
    for cmd in _commands["commands"]:
        cmd_category = cmd["category"]
        if cmd_category not in categories:
            categories[cmd_category] = []
        categories[cmd_category].append(CommandOption(cmd))


if __name__ == "__main__":
    folder = 'interactions'

    with open('reactions.json', 'rb+') as file:
        reactions = orjson.loads(file.read())

    if not os.path.exists(folder):
        os.mkdir(folder)
    new_reactions = defaultdict(dict)

    for name, data in reactions.items():
        for lang, desc in data.items():
            new_reactions[lang][name] = desc

    with open('new_reactions.json', 'wb+') as file:
        file.write(orjson.dumps(new_reactions))

    for lang, data in new_reactions.items():
        if not os.path.exists(os.path.join(folder, lang)):
            os.mkdir(os.path.join(folder, lang))
        for name, desc in data.items():
            cmd_data = {}
