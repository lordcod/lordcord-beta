import contextlib
import logging
from typing import Optional, Union, Any

import orjson
import nextcord
import asyncio
from datetime import datetime
from functools import lru_cache


from .misc import MISSING

_log = logging.getLogger(__name__)

class GenerateMessageError(Exception):
    pass


class GeneratorMessageDictPop(dict):
    def __init__(self, data):
        self.data = data
        super().__init__(data)

    def get(self, key, default=None):
        return self.data.pop(key, default)

    def __getitem__(self, key: Any) -> Any:
        return self.data.pop(key)


class GeneratorMessage:
    def __init__(self, data: Union[str, dict]) -> None:
        self.data = data

    @staticmethod
    def check_empty(data: dict) -> bool:
        return not any((data.get('content'), data.get('plainText'), data.get('embed'), data.get('embeds')))

    def decode_data(self):
        if not isinstance(self.data, dict):
            try:
                decode_data = orjson.loads(self.data)
            except orjson.JSONDecodeError as exc:
                _log.warning(f"Possible parsing error: {self.data}",
                             exc_info=exc)
                decode_data = self.data
        else:
            decode_data = self.data.copy()
        return decode_data if isinstance(decode_data, dict) else str(decode_data)

    def get_error(self, error_status: Optional[int] = None, with_exception: bool = True):
        if error_status == 5415:
            content = '**Content** and **plain text** cannot be combined.'
        elif error_status == 5410:
            content = '**Embed** and **embeds** cannot be combined.'
        elif error_status == 404:
            content = 'The message is empty.'
        else:
            content = 'Unknown message error.'
        if with_exception:
            raise GenerateMessageError(content)
        return {'content': content}

    @lru_cache()
    def parse(self, with_empty: bool = False, with_webhook: bool = False, with_exception: bool = True):
        data = self.decode_data()
        if isinstance(data, str):
            data = {'content': data}

        data.pop('attachments', MISSING)
        plain_text = data.pop('plainText', MISSING)
        content = data.pop('content', MISSING)
        embed = self.parse_embed(data)
        embeds = self.parse_embeds(data.pop('embeds', MISSING))
        flags = data.pop('flags', MISSING)
        username = data.pop('username', MISSING)
        avatar_url = data.pop('avatar_url', MISSING)

        if content is not MISSING and plain_text is not MISSING:
            return self.get_error(5415, with_exception)
        if embed is not MISSING and embeds is not MISSING:
            return self.get_error(5410, with_exception)

        ret = {}
        ret['content'] = content if content is not MISSING else plain_text if plain_text is not MISSING else None
        ret['embeds'] = [
            embed] if embed is not MISSING else embeds if embeds is not MISSING else []

        if flags is not MISSING:
            ret['flags'] = nextcord.MessageFlags._from_value(flags)
        if username is not MISSING and with_webhook:
            ret['username'] = username
        if avatar_url is not MISSING and with_webhook:
            ret['avatar_url'] = avatar_url
        if with_empty and self.check_empty(ret):
            return self.get_error(404, with_exception)
        return ret

    def parse_embed(self, data: dict):
        new_data = GeneratorMessageDictPop(data)
        
        with contextlib.suppress(KeyError):
            timestamp = data["timestamp"]
            if isinstance(timestamp, (int, float)):
                try:
                    # сначала пробуем как секунды
                    data["timestamp"] = datetime.fromtimestamp(
                        float(timestamp)).isoformat()
                except (OSError, OverflowError, ValueError):
                    # если не вышло - делим на 1000 (миллисекунды)
                    data["timestamp"] = datetime.fromtimestamp(
                        float(timestamp) / 1000).isoformat()


        with contextlib.suppress(KeyError, ValueError):
            color = data.pop("color")
            if isinstance(color, str) and color.startswith(('0x', '#')):
                color = int(color.removeprefix('#').removeprefix('0x'), 16)
            data["color"] = int(color)

        for arg in ('thumbnail', 'image'):
            with contextlib.suppress(KeyError):
                url = data[arg]
                if isinstance(url, str):
                    data[arg] = {'url': url}
                elif isinstance(url, dict) and not url.get('url', '').strip():
                    del data[arg]

        embed = nextcord.Embed.from_dict(new_data)
        if embed:
            return embed
        return MISSING

    def parse_embeds(self, data):
        if data is MISSING:
            return MISSING
        if not isinstance(data, list):
            return []
        return [embed for item in data if (embed := self.parse_embed(item)) is not MISSING]


async def clone_message(message: nextcord.Message) -> dict:
    content = message.content
    embeds = message.embeds
    files = await asyncio.gather(*[attach.to_file(spoiler=attach.is_spoiler()) for attach in message.attachments])
    return {"content": content, "embeds": embeds, "files": files}


def generate_message(content: str, *, with_empty: bool = False) -> dict:
    message = GeneratorMessage(content)
    return message.parse(with_empty)

if __name__ == '__main__':
    embed_data = {
        "title": "Thumbnail Test",
        "description": "With thumbnail",
        "thumbnail": "https://example.com/thumb.png"
    }
    result = generate_message(orjson.dumps(embed_data).decode())
    print(result)