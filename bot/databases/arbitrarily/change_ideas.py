from _connection import connection
import orjson
from psycopg2.extensions import register_adapter, AsIs


def adapt_dict(dict_var):
    return AsIs("'" + orjson.dumps(dict_var).decode() + "'")


register_adapter(dict, adapt_dict)


def change_data(guild_id, ideas):
    new_data = {}
    for name, value in ideas.items():
        new_data[name.replace("-", "_")] = value
    with connection.cursor() as cursor:
        cursor.execute("UPDATE guilds SET ideas = %s WHERE id = %s",
                       (new_data, guild_id,))
    print(new_data)


with connection.cursor() as cursor:
    cursor.execute(
        "SELECT id, ideas FROM guilds")
    values = cursor.fetchall()
    print(values)
    for id, ideas in values:
        if ideas:
            change_data(id, ideas)


print("Finish")
connection.close()
