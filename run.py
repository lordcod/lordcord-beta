from bot.misc.logger import setup_logging
setup_logging()


if __name__ == "__main__":
    from bot import main
    main.start_bot()
