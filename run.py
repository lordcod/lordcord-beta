import orjson
from cordlog import setup_logging

config_path = "assets/log_config.json"
with open(config_path, "rb") as f:
    config = orjson.loads(f.read())

setup_logging(config)


if __name__ == "__main__":
    from bot import main
    main.start_bot()
