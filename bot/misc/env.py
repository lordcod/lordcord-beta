from os import environ
from dotenv import load_dotenv

load_dotenv()


class Tokens:
    token = environ.get("token")
