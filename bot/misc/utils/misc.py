# bot/misc/misc.py
import functools
import random
import re
import nextcord
from functools import lru_cache

import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from typing import Any, Iterable, TypeVar, Union, Generic, Tuple

from colormath.color_objects import sRGBColor, LabColor
from colormath.color_conversions import convert_color
from colormath.color_diff import delta_e_cie2000

from PIL import Image, ImageFont, ImageDraw

SALT = b'lkGrd8F209'
MISSING = nextcord.utils._MissingSentinel()
T = TypeVar('T')

# Функции для работы с данными


def parse_fission(iterable: Iterable[T], count: int) -> list[list[T]]:
    ret = []
    for index, value in enumerate(iterable):
        ret_index = int(index // count)
        try:
            values = ret[ret_index]
        except IndexError:
            values = []
            ret.append(values)
        values.append(value)
    return ret


def randfloat(a: float | int, b: float | int, scope: int = 14) -> float:
    return random.randint(int(a*10**scope), int(b*10**scope)) / 10**scope


def clamp(val: Union[int, float], minv: Union[int, float], maxv: Union[int, float]) -> Union[int, float]:
    return min(maxv, max(minv, val))


def randquan(quan: int) -> int:
    if quan <= 0:
        raise ValueError
    return random.randint(10**(quan-1), int('9'*quan))


class AsyncSterilization(Generic[T]):
    def __init__(self, cls) -> None:
        self.cls = cls

    def __repr__(self) -> str:
        return f"<{type(self).__name__} {self.cls!r}>"

    async def __call__(self, *args: Any, **kwds: Any) -> T:
        self = self.cls.__new__(self.cls)
        await self.__init__(*args, **kwds)
        return self


def bool_filter(data: T) -> T:
    if isinstance(data, dict):
        return dict(filter(lambda item: item[1], data.items()))
    return type(data)(filter(bool, data))


def generate_random_token() -> Tuple[str, str]:
    message = randquan(100).to_bytes(100)
    key = Fernet.generate_key()
    token = Fernet(key).encrypt(message)
    return key.decode(), token.decode()


def decrypt_token(key: str, token: str) -> int:
    res = Fernet(key.encode()).decrypt(token.encode())
    return int.from_bytes(res)


def replace_dict_key(data: dict, old, new) -> dict:
    keys = list(data.keys())
    if old in keys:
        index = keys.index(old)
        keys[index] = new
    return {k if k != old else new: v for k, v in data.items()}


def add_gradient(
    background: Image.Image,
    font: ImageFont.FreeTypeFont,
    text: str,
    height: int,
    color_start: Tuple[int, int, int],
    color_stop: Tuple[int, int, int]
) -> None:
    w, h = font.getbbox(text)[2:]

    gradient = Image.new("RGB", (w, h))
    draw_gradient(gradient, color_start, color_stop)

    im_text = Image.new("RGBA", (w, h))
    d = ImageDraw.Draw(im_text)
    d.text((0, 0), text, font=font)

    background.draft("RGBA", background.size)
    background.paste(
        gradient,
        (int(background.size[0] / 2 - im_text.size[0] / 2), height),
        im_text
    )


def draw_gradient(img: Image.Image, start: Tuple[int, int, int], end: Tuple[int, int, int]):
    px = img.load()
    for y in range(0, img.height):
        color = tuple(int(start[i] + (end[i] - start[i])
                      * y / img.height) for i in range(3))
        for x in range(0, img.width):
            px[x, y] = color


def to_rgb(color: str | int):
    if isinstance(color, str):
        color = int(color.strip(' #0x')[:6], 16)

    def _get_byte(byte: int) -> int:
        return (color >> (8 * byte)) & 0xFF
    return _get_byte(2), _get_byte(1), _get_byte(0)


def get_distance(color1_lab, color2):
    color2_rgb = sRGBColor(*to_rgb(color2))
    color2_lab = convert_color(color2_rgb, LabColor)
    return delta_e_cie2000(color1_lab, color2_lab)


@lru_cache()
def get_award(number: int):
    return {1: '🥇', 2: '🥈', 3: '🥉'}.get(number, number)


def cut_back(string: str, length: int):
    return string if len(string) <= length else string[:length-3].strip() + "..."


class TranslatorFlags:
    def __init__(self, longopts: list[str] = []):
        """
        Инициализируем класс с допустимыми флагами.
        """
        self.longopts = longopts

    def convert(self, text: str) -> Any:
        """
        Преобразует строку текста в словарь флагов с их значениями.
        """
        # Регулярное выражение для флагов вида --flag или --flag=value
        flags = {}
        pattern = r'--([a-zA-Z0-9_-]+)(?:=([^\s]+))?'

        # Проверяем наличие флагов в строке
        matches = re.findall(pattern, text)

        if not matches:
            raise ValueError(
                "Invalid format: Fлаг должен быть в формате '--flag' или '--flag=value'")

        # Заполняем словарь флагов
        for match in matches:
            flag, value = match
            # Если флаг без значения, то считаем, что значение пустое
            if value is None:
                value = ''
            flags[flag] = value

        # Проверка на допустимость флагов
        invalid_flags = [
            flag for flag in flags if flag not in self.longopts]
        if invalid_flags:
            raise ValueError(f"Invalid flags: {', '.join(invalid_flags)}")

        return flags

    def __class_getitem__(cls, *args: str):
        """
        Создает экземпляр класса с переданными флагами.
        """
        return cls(args)


class Tokenizer:
    @staticmethod
    def encrypt(data: str, key: bytes) -> str:
        fernet = Fernet(key)
        encrypted_data = fernet.encrypt(data.encode())
        return base64.b64encode(encrypted_data).decode()

    @staticmethod
    def decrypt(encrypted_data: str, key: bytes) -> str:
        fernet = Fernet(key)
        encrypted_data = base64.b64decode(
            encrypted_data)
        decrypted_data = fernet.decrypt(encrypted_data).decode()
        return decrypted_data

    @staticmethod
    def generate_key(password: str) -> bytes:
        """
        Генерируем ключ шифрования на основе пароля с использованием PBKDF2.
        """
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=SALT,
            iterations=100000,
            backend=default_backend()
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key
