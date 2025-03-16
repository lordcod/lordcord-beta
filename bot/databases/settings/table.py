from __future__ import annotations
import asyncio
import logging
from typing import List
from nextcord import utils
import re
from .column import Colum
from ..db_engine import DataBase

_log = logging.getLogger(__name__)


def convert_default(default_text: str) -> str:
    if (
        isinstance(default_text, str) and
        (templete := re.fullmatch("'(.+)'::([a-zA-Z0-9]+)", default_text))
    ):
        return templete.group(1)
    return default_text


class TableAPI:
    def __init__(self, engine: DataBase, table_name: str) -> None:
        self.engine = engine
        self.table_name = table_name

    def register_colums(self, *columns: Colum):
        for c in columns:
            c.set_engine(self.engine)

    async def create(self) -> None:
        await self.engine.execute(
            f"CREATE TABLE IF NOT EXISTS {self.table_name} ()")

    async def get_colums(self) -> List[Colum]:
        colums = []
        results = await self.engine.fetchall("""
                    SELECT c.column_name, c.data_type, c.column_default, is_nullable::bool,
                    CASE WHEN EXISTS(SELECT 1 FROM INFORMATION_SCHEMA.constraint_column_usage k 
                        WHERE c.table_name = k.table_name and k.column_name = c.column_name) 
                        THEN true ELSE false END as primary_key
                    FROM INFORMATION_SCHEMA.COLUMNS c 
                    WHERE c.table_name=%s;
                """, (self.table_name,))
        for res in results:
            colums.append(Colum(
                name=res[0],
                data_type=res[1],
                default=convert_default(res[2]),
                nullable=res[3],
                primary_key=res[4]
            ))
        self.register_colums(*colums)
        return colums

    async def add_colum(self, colum: Colum, colums: List[Colum]) -> None:
        if not isinstance(colum, Colum):
            raise TypeError("The argument must match the Column type")

        if colum in colums:
            return

        if colum_with_name := utils.get(colums, name=colum.name):
            if colum.default != colum_with_name.default:
                await colum_with_name.change_default(self.table_name, colum.default)
                _log.debug("The default value of column %s has been changed in %s (%s-%s)", colum.name, self.table_name, colum.default, colum_with_name.default)

            if colum.data_type != colum_with_name.data_type:
                await colum_with_name.change_type(self.table_name, colum.data_type)
                _log.debug("The type of column %s has been changed in %s", colum.name, self.table_name)
            return

        _log.debug("Add column %s in %s", colum, self.table_name)
        await colum.add_colum(self.table_name)
        colums.append(colum)

    async def delete_ofter_colums(
        self,
        colums: List[Colum],
        reserved_colums: List[str]
    ) -> None:
        tasks = []
        for colum in colums:
            if colum.name not in reserved_colums:
                colums.remove(colum)
                tasks.append(colum.drop_colum(self.table_name))
        await asyncio.gather(*tasks)


class Table:
    __tablename__: str
    __columns__: List[Colum]
    __reserved_columns__: List[str]
    __force_columns__: bool = True

    def __init_subclass__(
        cls,
        *,
        force_columns: bool = True
    ) -> None:
        cls.__tablename__ = (cls.__tablename__ or cls.__name__).lower()
        cls.__columns__ = []
        cls.__reserved_columns__ = []
        cls.__force_columns__ = force_columns

        for name, item in cls.__dict__.items():
            if not isinstance(item, Colum):
                continue
            item.name = item.name or name
            cls.__reserved_columns__.append(item.name)
            cls.__columns__.append(item)

    @classmethod
    def set_engine(cls, engine: DataBase):
        cls.engine = engine

    @classmethod
    async def create(cls):
        tapi = TableAPI(cls.engine, cls.__tablename__)
        await tapi.create()

        cls.colums = await tapi.get_colums()
        tapi.register_colums(*cls.__columns__)

        for item in cls.__columns__:
            await tapi.add_colum(item, cls.colums)

        if cls.__force_columns__ is True:
            await tapi.delete_ofter_colums(cls.colums, cls.__reserved_columns__)
