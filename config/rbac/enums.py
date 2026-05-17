from enum import Enum
from typing import Self, cast, Iterable


class PermissionEnum(str, Enum):
    description: str
    category: str

    def __new__(cls, value: str, description: str, category: str) -> Self:
        str_cls = cast(type[str], cls)
        # noinspection PyTypeChecker
        instance = cast(Self, str.__new__(str_cls, value))
        instance._value_ = value
        return instance

    def __init__(self, _value: str, description: str, category: str) -> None:
        self.description = description
        self.category = category

    @property
    def key(self) -> str:
        return self.value


class RoleEnum(str, Enum):
    description: str
    system: bool
    permissions: tuple[PermissionEnum, ...]

    def __new__(cls, value: str, description: str, system: bool, permissions: Iterable[PermissionEnum] = (), ) -> Self:
        str_cls = cast(type[str], cls)
        # noinspection PyTypeChecker
        instance = cast(Self, str.__new__(str_cls, value))
        instance._value_ = value
        instance.description = description
        instance.system = system
        instance.permissions = tuple(permissions)

        return instance
