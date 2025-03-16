from os import environ
from dotenv import load_dotenv

load_dotenv()


class Tokens:
    token_lordcord = environ.get("lordcord_token")
    token_lordcord2 = environ.get("anprim_token")
    token_lordkind = environ.get("lordkind_token")
    token_lordсlassic = environ.get("lordclassic_token")
    token = environ.get("discord_token")
