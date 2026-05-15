# AGENTS.md

## Scope

This app owns append-only audit logging for legally relevant changes to BR Manager domain objects.

## Domain Rules

- `AuditEntry` is append-only. Never edit or delete existing audit entries.
- Audit entries use generic foreign keys to track any model instance.
- `action` field uses fixed choices: `CREATED`, `UPDATED`, `DELETED`, `FINALIZED`, `RECONFIRMED`.
- `actor` can be null if the action was system-driven or the user is deleted.
- Snapshots (`old_snapshot`, `new_snapshot`) and `metadata` are JSON fields for flexible structured data.

## Service Usage

- Use `apps.audit.services.create_audit_entry()` to create audit entries consistently.
- Service handles content type resolution, actor normalization, and default values.
- Always provide `target`, `action`, and `change_type` parameters.
- Snapshots and metadata are optional but should be provided when relevant for legal traceability.

## Integration Points

- Other apps should create audit entries for status transitions, finalizations, deletions, and other legally relevant changes.
- Do not create audit entries for trivial updates unless explicitly required by legal/compliance rules.
- Audit entries are read-only records; use them for compliance reporting and history views only.

## Checks

- Run `python manage.py test apps.audit` after model or service changes.
- Verify that audit entries are created correctly in domain-specific tests when touching audit-logged workflows.
