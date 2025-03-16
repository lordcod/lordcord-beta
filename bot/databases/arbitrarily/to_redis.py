from _connection import connection
from bot.misc import logger
import psycopg2.extras
import asyncio
from bot.databases import localdb


async def main():
    every_data = {}
    with connection.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
        cursor.execute('SELECT id FROM guilds')
        keys = cursor.fetchall()
        print(keys)
        for k in keys:
            cursor.execute('SELECT * FROM guilds WHERE id = %s', k)
            data = dict(cursor.fetchone())
            id = data.pop('id')
            every_data[id] = data
    data = await localdb.cache.get('guilds', every_data)
    print(data)
    await localdb.cache.close()

asyncio.run(main())
