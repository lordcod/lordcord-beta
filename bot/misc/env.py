from os import environ
from dotenv import load_dotenv

load_dotenv(override=True)

API_URL = environ['API_URL']
PROXY = environ.get('PROXY')
TELEGRAM_TOKEN = environ.get('TELEGRAM_TOKEN')
YANDEX_API_TOKEN = environ.get('yandex_api_token')

REDIS_HOST = environ.get('REDIS_HOST')
REDIS_PORT = environ.get('REDIS_PORT')
REDIS_PASSWORD = environ.get('REDIS_PASSWORD')

TWITCH_CLIENT_SECRET = environ.get('TWITCH_CLIENT_SECRET')
TWITCH_CLIENT_ID = environ.get('TWITCH_CLIENT_ID')

YOUTUBE_API_KEY = environ.get('YOUTUBE_API_KEY')

VK_CLIENT_ID = environ.get('VK_CLIENT_ID')

LOG_WEBHOOK = environ.get('log_webhook')


class Tokens:
    token = environ["token"]
