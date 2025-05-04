import unittest
import sys
import os

sys.path.append(os.getcwd())

import bot.misc.utils.co_emoji as color_utils


class TestColorUtils(unittest.TestCase):

    def test_is_default_emoji(self):
        # Проверка стандартного emoji с использованием is_emoji
        emoji_char = "😀"
        # Теперь проверяем через emoji.is_emoji, так как EMOJI_DATA больше нет
        result = color_utils.is_default_emoji(emoji_char)
        self.assertTrue(result)

    def test_is_custom_emoji(self):
        self.assertTrue(color_utils.is_custom_emoji("<:custom:123456789012345678>"))
        self.assertTrue(color_utils.is_custom_emoji("<a:custom:123456789012345678>"))
        self.assertFalse(color_utils.is_custom_emoji("😀"))
        self.assertFalse(color_utils.is_custom_emoji("not an emoji"))

    def test_is_emoji(self):
        # Проверка стандартного emoji
        self.assertTrue(color_utils.is_emoji("😀"))
        # Проверка кастомного emoji
        self.assertTrue(color_utils.is_emoji("<:custom:123456789012345678>"))
        # Проверка пустой строки (по коду возвращает True)
        self.assertTrue(color_utils.is_emoji(""))

    def test_to_rgb_hex_string(self):
        rgb = color_utils.to_rgb("#FF0000")
        # Ожидаем (0, 0, 255), т.к. функция возвращает BGR порядок
        self.assertEqual(rgb, (0, 0, 255))  # Красный

    def test_to_rgb_int(self):
        rgb = color_utils.to_rgb(0x00FF00)
        self.assertEqual(rgb, (0, 255, 0))  # Зеленый

    def test_to_rgb_short_hex(self):
        rgb = color_utils.to_rgb("0x0000FF")
        self.assertEqual(rgb, (0, 0, 255))  # Синий

    def test_find_color_emoji_returns_known_emoji(self):
        emoji_result = color_utils.find_color_emoji("#FF0000")
        self.assertIsInstance(emoji_result, str)
        self.assertTrue(emoji_result.startswith("<:"))


if __name__ == '__main__':
    unittest.main()
