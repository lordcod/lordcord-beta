import logging
import os
from redis.asyncio import ConnectionPool, StrictRedis
from typing import Optional
from bot.databases.misc import adapter

# Логгер
_log = logging.getLogger(__name__)

POOL = ConnectionPool(
    host=os.environ.get('REDIS_HOST'),
    port=os.environ.get('REDIS_PORT'),
    password=os.environ.get('REDIS_PASSWORD'),
    db=0
)
cache = StrictRedis(connection_pool=POOL, health_check_interval=30)


class DataStore:
    def __init__(self, table_name: str):
        self.table_name = table_name

    async def _get_data(self) -> Optional[dict]:
        """
        Получаем данные из Redis для конкретной таблицы базы данных.
        Ожидаем, что данные будут в формате JSON.
        """
        data = await cache.get(self.table_name)
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
        await cache.set(self.table_name, serialized_data)
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
