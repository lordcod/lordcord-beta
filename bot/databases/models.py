import os
from socket import getnameinfo
from tortoise.models import Model
from tortoise.expressions import Q
from tortoise import fields, Tortoise, run_async
import sys

sys.path.append(os.getcwd())


if True:
    from bot.resources import info
    from bot.databases.misc import adapter


class JSONField(fields.JSONField):
    def __init__(self, **kwargs):
        super().__init__(
            encoder=adapter.dumps,
            decoder=adapter.loads,
            **kwargs
        )


class GuildModel(Model):
    class Meta:
        table = "guilds"

    id = fields.BigIntField(primary_key=True)
    language = fields.TextField(default=info.DEFAULT_LANGUAGE)
    prefix = fields.TextField(default=info.DEFAULT_PREFIX)
    color = fields.BigIntField(default=info.DEFAULT_COLOR)
    prefix = fields.TextField(
        default=info.DEFAULT_PREFIX)
    color = fields.BigIntField(default=info.DEFAULT_COLOR)
    system_emoji = fields.BigIntField(
        default=info.DEFAULT_BOT_COLOR)
    economic_settings = JSONField(default=info.DEFAULT_ECONOMY_SETTINGS)
    music_settings = JSONField(default={})
    auto_roles = JSONField(default={})
    invites = JSONField(default={})
    giveaways = JSONField(default={})
    tickets = JSONField(default={})
    thread_messages = JSONField(default={})
    reactions = JSONField(default={})
    auto_translate = JSONField(default={})
    polls = JSONField(default={})
    greeting_message = JSONField(default={})
    command_permissions = JSONField(default={})
    ideas = JSONField(default={})
    logs = JSONField(default={})
    role_reactions = JSONField(default={})
    delete_task = fields.BigIntField(default=0)
    tempvoice = JSONField(default={})
    farewell_message = JSONField(default={})
    message_state = JSONField(default={})
    voice_time_state = JSONField(default={})
    score_state = JSONField(default={})
    level_state = JSONField(default={})
    thread_roles = JSONField(default={})
    thread_open = JSONField(default={})

    # NOTIFICATION

    twitch_notification = JSONField(default={})
    youtube_notification = JSONField(default={})
    vk_notification = JSONField(default={})
    telegram_notification = JSONField(default={})


# TEMP BLOCK
# class BaseNotificationModel(Model):
#     id = fields.CharField(20, primary_key=True)
#     guild_id = fields.IntField()
#     channel_id = fields.IntField()
#     message = fields.TextField()

#     class Meta:
#         abstract = True


class EconomicModel(Model):
    class Meta:
        table = "economic"

    guild_id = fields.BigIntField()
    member_id = fields.BigIntField()
    balance = fields.BigIntField(default=0)
    bank = fields.BigIntField(default=0)
    daily = fields.BigIntField(default=0)
    weekly = fields.BigIntField(default=0)
    monthly = fields.BigIntField(default=0)
    rob = fields.BigIntField(default=0)
    conclusion = fields.BigIntField(default=0)
    work = fields.BigIntField(default=0)


class RoleModel(Model):
    class Meta:
        table = "roles"

    guild_id = fields.BigIntField()
    member_id = fields.BigIntField()
    role_id = fields.BigIntField(null=True)
    time = fields.BigIntField(null=True)
    system = fields.BooleanField(null=True)


class BanModel(Model):
    class Meta:
        table = "bans"

    guild_id = fields.BigIntField()
    member_id = fields.BigIntField()
    time = fields.BigIntField(null=True)


if __name__ == '__main__':
    async def main():
        await Tortoise.init(
            db_url="sqlite://db/.sqlite3",
            modules={'models': ['__main__']},
        )
        await Tortoise.generate_schemas(safe=True)

        g = await GuildModel.get(id=1179069504186232852)
        g.vk_notification = {
            'nesog': {
                'id': 'nesog',
                'group_id': 222485128,
                'channel_id': 1179069504651796562
            }
        }
        await g.save()
    run_async(main())
