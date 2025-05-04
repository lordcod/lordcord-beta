import os
import sys
import unittest
import orjson
from nextcord import Embed

sys.path.append(os.getcwd())

if True:
    from bot.misc.utils.messages import GeneratorMessage, generate_message, GenerateMessageError


class TestGeneratorMessage(unittest.TestCase):

    def test_simple_content(self):
        data = {"content": "Hello, World!"}
        result = generate_message(orjson.dumps(data).decode())
        self.assertEqual(result['content'], "Hello, World!")
        self.assertEqual(result['embeds'], [])

    def test_plain_text(self):
        data = {"plainText": "Plain message"}
        result = generate_message(orjson.dumps(data).decode())
        self.assertEqual(result['content'], "Plain message")
        self.assertEqual(result['embeds'], [])

    def test_embed(self):
        embed_data = {
            "title": "Test Title",
            "description": "Test Description",
            "color": "#00FF00"
        }
        data = orjson.dumps(embed_data).decode()
        result = generate_message(data)
        self.assertIsInstance(result['embeds'][0], Embed)
        self.assertEqual(result['embeds'][0].title, "Test Title")
        self.assertEqual(result['embeds'][0].description, "Test Description")

    def test_invalid_json(self):
        invalid_data = "{invalid_json: true}"
        result = generate_message(invalid_data)
        self.assertEqual(result['content'], "{invalid_json: true}")
        self.assertEqual(result['embeds'], [])

    def test_timestamp_parsing_seconds(self):
        embed_data = {
            "title": "Timestamp Test",
            "timestamp": 1714828893,  # timestamp in seconds
        }
        data = orjson.dumps(embed_data).decode()
        result = generate_message(data)
        embed = result['embeds'][0]
        self.assertIsInstance(embed, Embed)
        self.assertEqual(embed.title, "Timestamp Test")
        self.assertIsNotNone(embed.timestamp)

    def test_timestamp_parsing_milliseconds(self):
        embed_data = {
            "title": "Timestamp Test",
            "timestamp": 1714828893000,  # timestamp in milliseconds
        }
        data = orjson.dumps(embed_data).decode()
        result = generate_message(data)
        embed = result['embeds'][0]
        self.assertIsInstance(embed, Embed)
        self.assertEqual(embed.title, "Timestamp Test")
        self.assertIsNotNone(embed.timestamp)

    def test_thumbnail_parsing(self):
        embed_data = {
            "title": "Thumbnail Test",
            "thumbnail": "https://example.com/thumb.png"
        }
        data = orjson.dumps(embed_data).decode()
        result = generate_message(data)
        embed = result['embeds'][0]
        self.assertIsInstance(embed, Embed)
        self.assertIn('thumbnail', embed.to_dict())
        self.assertEqual(embed.to_dict()['thumbnail']['url'], "https://example.com/thumb.png")

    def test_color_hex(self):
        embed_data = {
            "title": "Color Test",
            "color": "#FF00FF"
        }
        data = orjson.dumps(embed_data).decode()
        result = generate_message(data)
        embed = result['embeds'][0]
        self.assertIsInstance(embed, Embed)
        self.assertEqual(embed.color.value, 0xFF00FF)

    def test_content_and_plaintext_error(self):
        data = {
            "content": "Hello",
            "plainText": "World"
        }
        with self.assertRaises(GenerateMessageError) as cm:
            GeneratorMessage(orjson.dumps(data).decode()).parse(with_exception=True)
        self.assertIn("Content", str(cm.exception))
        
    def test_embed_and_embeds_error(self):
        data = {
            "title": "Embed 1",
            "embeds": [{"title": "Embed 2"}]
        }
        with self.assertRaises(GenerateMessageError) as cm:
            GeneratorMessage(orjson.dumps(data).decode()).parse(with_exception=True)
        self.assertIn("Embed", str(cm.exception))


    def test_empty_message_error(self):
        data = {}
        with self.assertRaises(GenerateMessageError) as cm:
            GeneratorMessage(orjson.dumps(data).decode()).parse(with_empty=True, with_exception=True)
        self.assertIn("empty", str(cm.exception))

    def test_flags(self):
        data = {
            "content": "Test",
            "flags": 4  # Example: SUPPRESS_EMBEDS
        }
        result = generate_message(orjson.dumps(data).decode())
        self.assertEqual(result['content'], "Test")
        self.assertTrue(result['flags'].value & 4)

    def test_with_webhook(self):
        data = {
            "content": "Test webhook",
            "username": "Bot",
            "avatar_url": "https://example.com/avatar.png"
        }
        gm = GeneratorMessage(orjson.dumps(data).decode())
        result = gm.parse(with_webhook=True)
        self.assertEqual(result['username'], "Bot")
        self.assertEqual(result['avatar_url'], "https://example.com/avatar.png")

    def test_embeds_list(self):
        embed_list = [{
            "title": "First Embed"
        }, {
            "title": "Second Embed"
        }]
        data = {
            "embeds": embed_list
        }
        result = generate_message(orjson.dumps(data).decode())
        self.assertEqual(len(result['embeds']), 2)
        self.assertEqual(result['embeds'][0].title, "First Embed")
        self.assertEqual(result['embeds'][1].title, "Second Embed")


if __name__ == '__main__':
    unittest.main()
