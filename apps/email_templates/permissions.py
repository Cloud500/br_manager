"""Permission helpers for e-mail template management."""


def user_can_manage_email_templates(user) -> bool:
    """Return whether a user may edit system e-mail templates."""
    if not user.is_authenticated:
        return False
    if user.is_superuser or user.is_staff:
        return True

    from apps.committees.models import Membership

    return Membership.objects.filter(
        user=user,
        is_active=True,
        deleted_at__isnull=True,
        role__permissions__codename="email_template.edit",
    ).exists()
