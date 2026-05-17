from apps.memberships.models import Membership

def crud_permissions(
        resource: str,
        category: str,
        labels: dict | None = None,
):
    labels = labels or {}

    defaults = {
        "create": "Erstellen",
        "view": "Ansehen",
        "edit": "Bearbeiten",
        "delete": "Löschen",
    }

    defaults.update(labels)

    return {
        action: (
            f"{resource}.{action}",
            f"{text}",
            category,
        )
        for action, text in (
            defaults.items()
        )
    }

def get_role_for_user_in_committee(user, committee):
    try:
        membership = Membership.objects.select_related("role").get(
            user=user,
            committee=committee,
        )
        return membership.role
    except Membership.DoesNotExist:
        return None

def has_permission(user, permission_key, committee):
    role = get_role_for_user_in_committee(user, committee)

    if not role:
        return False

    return role.permissions.filter(key=permission_key).exists()