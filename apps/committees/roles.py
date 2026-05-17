from config.rbac.enums import RoleEnum
from config.rbac.registry import register_roles
from apps.committees.permissions import CommitteePermission


@register_roles
class CommitteeRole(RoleEnum):

    CHAIR = (
        "chair",
        "Gremium/Ausschuss Vorsitz",
        False,
        [CommitteePermission.CREATE, CommitteePermission.EDIT],
    )


# Erweiterung bsp.
# from config.rbac.registry import ROLE_REGISTRY
#
#
# ROLE_REGISTRY["chair"].permissions += (CommitteePermission.DELETE, )