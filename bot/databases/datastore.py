import logging
from redis.asyncio import ConnectionPool, StrictRedis
from typing import Optional
from bot.databases.misc import adapter
from bot.misc.env import REDIS_HOST, REDIS_PASSWORD, REDIS_PORT

# Логгер
_log = logging.getLogger(__name__)

if REDIS_HOST is not None:
    POOL = ConnectionPool(
        host=REDIS_HOST,
        port=REDIS_PORT,
        password=REDIS_PASSWORD,
        db=0
    )
    cache = StrictRedis(connection_pool=POOL, health_check_interval=30)
else:
    POOL = cache = None


class DataStore:
    def __init__(self, table_name: str):
        self.table_name = table_name

        self.__with_redis = bool(cache)
        if not self.__with_redis:
            self.__cache = {}

    async def _get_data(self) -> Optional[dict]:
        """
        Получаем данные из Redis для конкретной таблицы базы данных.
        Ожидаем, что данные будут в формате JSON.
        """
        if self.__with_redis:
            data = await cache.get(self.table_name)
        else:
            data = self.__cache.get(self.table_name)

        if data:
            return adapter.loads(data)
        return {}

    async def _set_data(self, data: dict) -> None:
        """
        Сохраняем данные в Redis для конкретной таблицы базы данных.
        Преобразуем данные в формат JSON перед сохранением.
        """
        serialized_data = adapter.dumps(data)
        if self.__with_redis:
            await cache.set(self.table_name, serialized_data)
        else:
            self.__cache[self.table_name] = serialized_data

    async def get(self, key, default=None):
        data = await self._get_data()
        if not data:
            _log.trace(f"No cached data found for table '{self.table_name}'.")

        return data.get(key, default)

    async def set(self, key, value) -> None:
        current_data = await self._get_data()
        current_data[key] = value

        await self._set_data(current_data)

    async def multi_set(self, pairs):
        current_data = await self._get_data()
        for key, value in pairs:
            current_data[key] = value

        await self._set_data(current_data)
    
    async def multi_get(self, keys):
        current_data = await self._get_data()
        values = []
        for key in keys:
            try:
                values.append(current_data[key])
            except KeyError as exc:
                _log.exception("Error in datastore",
                               exc_info=exc)
                continue
        return values

    async def increment(self, key, delta=1):
        value = await self.get(key, 0)
        await self.set(key, value+delta)

    async def delete(self, key) -> bool:
        current_data = await self._get_data()
        if key in current_data:
            current_data.pop(key)
            await self._set_data(current_data)
            return True
        return False

    async def exists(self, key) -> bool:
        current_data = await self._get_data()
        return key in current_data

    fetch = _get_data
