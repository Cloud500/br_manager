from config.rbac.enums import PermissionEnum
from config.rbac.registry import register_permissions
from config.rbac.services import crud_permissions

CRUD = crud_permissions(
    resource="committees.committee",
    category="committees",
)

@register_permissions
class CommitteePermission(PermissionEnum):
    CREATE = CRUD["create"]
    VIEW = CRUD["view"]
    EDIT = CRUD["edit"]
    DELETE = CRUD["delete"]
    CREATE_SUB_COMMITTEE = (
        "committees.committee.create_sub_committee",
        "Darf Untergremien erstellen",
        "committees",
    )
