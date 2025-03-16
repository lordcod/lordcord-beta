from __future__ import annotations
from typing import Optional
from ..db_engine import DataBase
from .posttype import PostType


class Colum:
    engine: DataBase

    def __init__(
        self,
        *,
        name: Optional[str] = None,
        data_type: str,
        default: Optional[str] = None,
        primary_key: Optional[bool] = False,
        nullable: Optional[bool] = False
    ) -> None:
        data_type = data_type.upper()

        self.name = name
        self.data_type = data_type if isinstance(
            data_type, PostType) else PostType.get(data_type)
        self.primary_key = primary_key
        self.nullable = nullable
        self.default = default

    def set_engine(self, engine: DataBase):
        self.engine = engine

    async def add_colum(self, table_name: str) -> None:
        await self.engine.execute(
            f"""
                ALTER TABLE {table_name}
                ADD {self.name} {self.data_type.value}
                {" PRIMARY KEY" if self.primary_key is True else ""}
                {" NOT NULL" if self.nullable is True else ""}
                {f" DEFAULT '{self.default}'" if self.default is not None else ""}
            """
        )

    async def drop_colum(self, table_name: str) -> None:
        await self.engine.execute(
            f"""
                ALTER TABLE {table_name}
                DROP COLUMN {self.name};
            """
        )

    async def change_name(self, table_name: str, new_name: str) -> None:
        self.name = new_name
        await self.engine.execute(
            f"""
                ALTER TABLE {table_name}
                RENAME COLUMN {self.name} TO {new_name};
            """
        )

    async def change_default(self, table_name: str, new_default: str) -> None:
        self.default = new_default
        await self.engine.execute(
            f"""
                ALTER TABLE {table_name}
                ALTER COLUMN {self.name} SET DEFAULT '{new_default}';
            """
        )

    async def change_type(self, table_name: str, new_type: PostType) -> None:
        await self.engine.execute(
            f"""
                ALTER TABLE {table_name}
                ALTER COLUMN {self.name} TYPE {new_type.value};
            """
        )

    def __repr__(self) -> str:
        return (f"<Colums name=\"{self.name}\" data_type=\"{self.data_type}\" "
                f"default=\"{self.default}\" primary_key={self.primary_key} "
                f"nullable={self.nullable}>")

    def __hash__(self) -> int:
        return hash(self.name)

    def __eq__(self, __value: object) -> bool:
        if not isinstance(__value, Colum):
            return False
        return (
            self.name == __value.name and
            self.data_type == __value.data_type and
            self.default == __value.default and
            self.primary_key == __value.primary_key and
            self.nullable == __value.nullable
        )

    def __ne__(self, __value: object) -> bool:
        if not isinstance(__value, Colum):
            return True
        return (
            self.name != __value.name or
            self.data_type != __value.data_type or
            self.default != __value.default or
            self.primary_key != __value.primary_key or
            self.nullable != __value.nullable
        )
