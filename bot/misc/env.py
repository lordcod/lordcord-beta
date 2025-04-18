from os import environ
from dotenv import load_dotenv

load_dotenv(override=True)


class Tokens:
    token = environ["token"]
    log_webhook = environ.get('log_webhook')
