from bot.databases.db_engine import DataBase
from bot.databases.handlers import establish_connection
from .settings import Table, Colum, PostType
from bot.resources import info


class GuildsDB(Table):
    __tablename__ = "guilds"

    id = Colum(data_type=PostType.BIGINT, primary_key=True)
    language = Colum(data_type=PostType.TEXT,
                     default=info.DEFAULT_LANGUAGE)
    prefix = Colum(data_type=PostType.TEXT,
                   default=info.DEFAULT_PREFIX)
    color = Colum(data_type=PostType.BIGINT, default=info.DEFAULT_COLOR)
    system_emoji = Colum(data_type=PostType.BIGINT, default=info.DEFAULT_BOT_COLOR)
    economic_settings = Colum(data_type=PostType.JSON,
                              default=info.DEFAULT_ECONOMY_SETTINGS_JSON)
    music_settings = Colum(data_type=PostType.JSON, default="{}")
    auto_roles = Colum(data_type=PostType.JSON, default="{}")
    invites = Colum(data_type=PostType.JSON, default="{}")
    giveaways = Colum(data_type=PostType.JSON, default="{}")
    tickets = Colum(data_type=PostType.JSON, default="{}")
    thread_messages = Colum(data_type=PostType.JSON, default="{}")
    reactions = Colum(data_type=PostType.JSON, default="{}")
    auto_translate = Colum(data_type=PostType.JSON, default="{}")
    polls = Colum(data_type=PostType.JSON, default="{}")
    greeting_message = Colum(data_type=PostType.JSON, default="{}")
    command_permissions = Colum(data_type=PostType.JSON, default="{}")
    ideas = Colum(data_type=PostType.JSON, default="{}")
    logs = Colum(data_type=PostType.JSON, default="{}")
    role_reactions = Colum(data_type=PostType.JSON, default="{}")
    delete_task = Colum(data_type=PostType.BIGINT, default=0)
    tempvoice = Colum(data_type=PostType.JSON, default="{}")
    twitch_notification = Colum(data_type=PostType.JSON, default="{}")
    youtube_notification = Colum(data_type=PostType.JSON, default="{}")
    farewell_message = Colum(data_type=PostType.JSON, default="{}")
    message_state = Colum(data_type=PostType.JSON, default="{}")
    voice_time_state = Colum(data_type=PostType.JSON, default="{}")
    score_state = Colum(data_type=PostType.JSON, default="{}")
    level_state = Colum(data_type=PostType.JSON, default="{}")
    thread_roles = Colum(data_type=PostType.JSON, default="{}")
    thread_open = Colum(data_type=PostType.JSON, default="{}")


class EconomicDB(Table):
    __tablename__ = "economic"

    guild_id = Colum(data_type=PostType.BIGINT, nullable=True)
    member_id = Colum(data_type=PostType.BIGINT, nullable=True)
    balance = Colum(data_type=PostType.BIGINT, default="0")
    bank = Colum(data_type=PostType.BIGINT, default="0")
    daily = Colum(data_type=PostType.BIGINT, default="0")
    weekly = Colum(data_type=PostType.BIGINT, default="0")
    monthly = Colum(data_type=PostType.BIGINT, default="0")
    rob = Colum(data_type=PostType.BIGINT, default="0")
    conclusion = Colum(data_type=PostType.BIGINT, default="0")
    work = Colum(data_type=PostType.BIGINT, default="0")


class RolesDB(Table):
    __tablename__ = "roles"

    guild_id = Colum(data_type=PostType.BIGINT, nullable=True)
    member_id = Colum(data_type=PostType.BIGINT, nullable=True)
    role_id = Colum(data_type=PostType.BIGINT, nullable=True)
    time = Colum(data_type=PostType.BIGINT, nullable=True)
    system = Colum(data_type=PostType.BOOLEAN)


class BansDB(Table):
    __tablename__ = "bans"

    guild_id = Colum(data_type=PostType.BIGINT, nullable=True)
    member_id = Colum(data_type=PostType.BIGINT, nullable=True)
    time = Colum(data_type=PostType.BIGINT, nullable=True)


class MongoDataBases(Table):
    __tablename__ = "mongo"

    name = Colum(data_type=PostType.TEXT, primary_key=True)
    values = Colum(data_type=PostType.JSON, default="{}")


_tables = [GuildsDB, EconomicDB, RolesDB, BansDB, MongoDataBases]
