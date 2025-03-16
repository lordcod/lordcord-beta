from _connection import connection
from bot.misc import logger
from bot.databases import localdb
import asyncio


async def main():
    with connection.cursor() as cursor:
        cursor.execute(
            """
                        SELECT values
                        FROM mongo 
                        WHERE name = 'ideas'
                    """)

        cache = await localdb.get_table('ideas')
        val = cursor.fetchone()
        data = val[0]
        data.update(cache._cache)
        data = dict(map(lambda item: (
            f"__CONVERT_NUMBER__ INTEGER {item[0]}", item[1]), data.items()))
        localdb.current_updated_task['ideas'] = data
        await localdb._update_db(__name__)
        await localdb.cache.close()


print("Finish")
asyncio.run(main())
connection.close()
