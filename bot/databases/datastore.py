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

        _log.trace('Load data from %s database: %s', self.table_name, data)
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

        _log.trace('Updated data from %s database: %s',
                   self.table_name, serialized_data)

    async def get(self, key, default=None):
        data = await self._get_data()
        if not data:
            _log.trace(f"No cached data found for table '{self.table_name}'.")

        return data.get(key, default)

    async def set(self, key, value) -> None:
        current_data = await self._get_data()
        current_data[key] = value

        await self._set_data(current_data)

    async def increment(self, key, delta=1):
        value = await self.get(key)
        await self.set(key, value+delta)

    fetch = _get_data
