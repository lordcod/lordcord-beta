
TORTOISE_ORM = {
    "connections": {
        "default": {
            "engine": "tortoise.backends.sqlite",
            "credentials": {
                "file_path": "db/.sqlite3"
            }
        }
    },
    "apps": {
        "models": {
            "models": [
                "bot.databases.models",
                "aerich.models"
            ],
            "default_connection": "default"
        }
    }
}
