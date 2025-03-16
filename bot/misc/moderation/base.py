from typing import TYPE_CHECKING, Any, Dict, Self, Tuple, get_origin


class BaseCache:
    __cache: Dict[Tuple[int, int], 'BaseCache'] = {}
    guild_id: int
    member_id: int
    data: Dict[Any, Any]

    def __new__(
        cls,
        guild_id: int,
        member_id: int
    ) -> Self:
        try:
            self = cls.__cache[(guild_id, member_id)]
        except KeyError:
            self = super().__new__(cls)
            cls.__cache[(guild_id, member_id)] = self
            self.guild_id = guild_id
            self.member_id = member_id

            data_annot = cls.__annotations__.get('data', None)
            if data_annot is not None:
                try:
                    if clsa := get_origin(data_annot):
                        self.data = clsa()
                    else:
                        self.data = data_annot()
                except Exception:
                    pass

        return self

    if TYPE_CHECKING:
        def __init__(
            self,
            guild_id: int,
            member_id: int
        ) -> None:
            pass

    def __eq__(self, value: object) -> bool:
        return (
            isinstance(value, type(self))
            and self.guild_id == value.guild_id
            and self.member_id == self.member_id
        )

    def __repr__(self) -> str:
        return '%s(guild_id=%s, member_id=%s)' % (type(self).__name__, self.guild_id, self.member_id)

    def __hash__(self) -> int:
        return int(f'{self.guild_id}{self.member_id}')
