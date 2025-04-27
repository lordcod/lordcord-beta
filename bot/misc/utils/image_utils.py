import copy
import logging
from typing import Tuple
from PIL import Image, ImageFont, ImageDraw
import io
import nextcord
from aiohttp import ClientSession


from bot.misc.utils.templates import lord_format
from bot.misc.utils.payloads import get_payload

_log = logging.getLogger(__name__)
cached = {}


class WelcomeImageGenerator:
    def __init__(self, member: nextcord.Member, session: ClientSession, config: dict):
        self.member = member
        self.session = session
        self.config = config

    async def load_bytes(self, path_or_url: str) -> io.BytesIO | str:
        if path_or_url in cached:
            return copy.copy(cached[path_or_url])

        if path_or_url.startswith("http"):
            async with self.session.get(path_or_url) as resp:
                if not resp.ok:
                    raise Exception("Failed to load from %s %s" %
                                    (path_or_url, resp.status))
                ret_bytes = await resp.read()
            ret = io.BytesIO(ret_bytes)
        else:
            ret = path_or_url
        cached[path_or_url] = copy.copy(ret)
        return ret

    # Функция для загрузки изображени
    async def load_image(self, path_or_url: str) -> Image.Image:
        res = await self.load_bytes(path_or_url)
        return Image.open(res).convert("RGBA")

    # Функция для загрузки шрифта
    async def load_font(self, path_or_url: str, size: int) -> ImageFont.FreeTypeFont:
        res = await self.load_bytes(path_or_url)
        return ImageFont.truetype(res, size)

    def add_round_corners(self, im: Image.Image, rad: int, border_width: int = 0, border_color: tuple = (0, 0, 0)) -> Image.Image:
        new_width, new_height = im.size

        # Создаем новое изображение для вывода
        rounded = Image.new("RGBA", im.size, (0, 0, 0, 0))

        mask = Image.new("L", im.size, 0)
        mask_draw = ImageDraw.Draw(mask)

        mask_draw.rounded_rectangle(
            [(border_width, border_width), (new_width -
                                            border_width, new_height - border_width)],
            radius=rad - border_width,
            fill=255
        )

        rounded.paste(im, (0, 0), mask=mask)

        if border_width > 0:
            draw = ImageDraw.Draw(rounded)
            draw.rounded_rectangle(
                [(border_width // 2, border_width // 2),
                 (new_width - border_width // 2, new_height - border_width // 2)],
                radius=rad,
                outline=border_color,
                width=border_width
            )

        return rounded

    def draw_gradient(self, img: Image.Image, text: str, font: ImageFont.FreeTypeFont, x: int, y: int,
                      color_start: Tuple[int, int, int], color_stop: Tuple[int, int, int], max_width: int):
        # Определяем ширину и высоту текста
        w, h = font.getbbox(text)[2:]

        # Создаем изображение для градиента
        gradient = Image.new("RGB", (w, h))
        self._draw_gradient(gradient, color_start, color_stop)

        # Создаем изображение для текста
        im_text = Image.new("RGBA", (w, h))
        d = ImageDraw.Draw(im_text)
        d.text((0, 0), text, font=font)

        # Позиционируем и вставляем градиент
        img.draft("RGBA", img.size)
        img.paste(
            gradient, (int(img.size[0] / 2 - im_text.size[0] / 2), y), im_text)

        # Функция для рисования градиента
    def _draw_gradient(self, img: Image.Image, start: Tuple[int, int, int], end: Tuple[int, int, int]):
        px = img.load()
        for y in range(0, img.height):
            color = tuple(
                int(start[i] + (end[i] - start[i]) * y / img.height) for i in range(3))
            for x in range(0, img.width):
                px[x, y] = color

    # Функция для рисования текста

    def draw_simple_text(self, background: Image.Image, text: str, font: ImageFont.FreeTypeFont, x: int, y: int, fill: str):
        draw = ImageDraw.Draw(background)
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        draw.text((x - text_width // 2, y), text, font=font, fill=fill)

    # Функция для обработки изображений (круглое или квадратное)
    def process_image(self, img: Image.Image, size: tuple, border: dict) -> Image.Image:
        img = img.resize(size)
        border_radius = border.get('radius', 0)
        border_width = border.get('width', 0)
        border_color = border.get('color', (0, 0, 0))
        if border_radius > 0:
            img = self.add_round_corners(
                img, border_radius, border_width, border_color)
        return img

    # Функция для обработки всех изображений в конфиге
    async def process_images(self, background: Image.Image) -> Image.Image:
        for image_conf in self.config.get("images", []):
            _log.debug('Loading image %s %s', image_conf.get(
                "type", "image"), image_conf.get("path") or image_conf.get("target", "member"))
            img_type = image_conf.get("type", "image")
            img = None

            if img_type == "image":
                img = await self.load_image(image_conf["path"])
            elif img_type == "avatar":
                avatar_url = image_conf.get("target", "member")
                if avatar_url == "member":
                    img = await self.load_image(self.member.display_avatar.url)
                elif avatar_url == "guild":
                    img = await self.load_image(self.member.guild.icon.url)
            else:
                raise ValueError(f"Unknown image type: {img_type}")
            _log.debug('Image data uploaded')

            size = tuple(image_conf.get("size", (100, 100)))
            border = image_conf.get("border", {})
            img = self.process_image(img, size, border)

            pos = tuple(image_conf.get("position", (0, 0)))
            background.paste(img, pos, mask=img if img.mode ==
                             "RGBA" else None)

        return background

    # Функция для добавления текста
    async def process_texts(self, background: Image.Image) -> None:
        for text_conf in self.config.get("texts", []):
            _log.debug('Load text %s', text_conf["type"])
            font_path = text_conf["font_path"]
            font_size = text_conf["font_size"]
            font = await self.load_font(font_path, font_size)

            context = get_payload(member=self.member)
            text = lord_format(text_conf["text"], context)

            x, y = text_conf.get("x", background.width //
                                 2), text_conf.get("y", 0)
            color = text_conf.get("fill", "#FFFFFF")

            if text_conf["type"] == "gradient":
                self.draw_gradient(background, text, font, x, y,
                                   text_conf["color_start"], text_conf["color_stop"], text_conf["max_width"])
            else:
                self.draw_simple_text(background, text, font, x, y, color)

    # Главная функция для генерации изображения
    async def generate(self) -> io.BytesIO:
        _log.debug('Start generate image')
        background = await self.load_image(self.config['background']['url'])
        background = background.resize((self.config['background'].get(
            "width", 800), self.config['background'].get("height", 450)))
        _log.debug('Loaded background')

        # Обрабатываем изображения
        background = await self.process_images(background)

        # Обрабатываем тексты
        await self.process_texts(background)

        _log.debug('The download is completed.')

        output = io.BytesIO()
        background.save(output, format="PNG")
        output.seek(0)
        return output
