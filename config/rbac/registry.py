from typing import Type, Dict

from .enums import PermissionEnum, RoleEnum

PERMISSION_REGISTRY: Dict[str, PermissionEnum] = {}
ROLE_REGISTRY: dict[str, RoleEnum] = {}


def register_permissions(enum_cls: Type[PermissionEnum], ):
    for permission in enum_cls:

        if permission.value in PERMISSION_REGISTRY:
            raise ValueError(f"Duplicate permission: {permission.value}")

        PERMISSION_REGISTRY[permission.value] = permission

    return enum_cls


def register_roles(enum_cls: type[RoleEnum]):
    for role in enum_cls:
        if role.value in ROLE_REGISTRY:
            raise ValueError(f"Duplicate role: {role.value}")

        ROLE_REGISTRY[role.value] = role

    return enum_cls
