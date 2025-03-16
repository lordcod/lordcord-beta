from psycopg2.extras import DictCursor
from _connection import connection

guild_id = 1179069504186232852

with connection.cursor(cursor_factory=DictCursor) as cursor:
    cursor.execute("SELECT * FROM economic WHERE guild_id = %s", (guild_id,))

    val = cursor.fetchone()

    print(type(val), dir(val))

print("Finish")
connection.close()
