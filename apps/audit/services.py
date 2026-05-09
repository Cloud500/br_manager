"""Service helpers for append-only audit logging."""

from django.contrib.contenttypes.models import ContentType

from apps.audit.models import AuditEntry


def create_audit_entry(
    *,
    target,
    action: str,
    change_type: str,
    actor=None,
    old_snapshot: dict | None = None,
    new_snapshot: dict | None = None,
    metadata: dict | None = None,
) -> AuditEntry:
    """Create an append-only audit entry for the target object."""
    content_type = ContentType.objects.get_for_model(target, for_concrete_model=False)
    return AuditEntry.objects.create(
        content_type=content_type,
        object_id=str(target.pk),
        action=action,
        actor=actor if getattr(actor, "is_authenticated", False) else None,
        change_type=change_type,
        old_snapshot=old_snapshot or {},
        new_snapshot=new_snapshot or {},
        metadata=metadata or {},
    )
