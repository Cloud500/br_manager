# AGENTS.md

## Scope

This app owns editable email templates, rendered-email helper records, template sanitization/text extraction, template permissions, and default template seed data.

## Rules

- Keep HTML sanitizing and plain-text extraction server-side; do not trust editor/client output.
- Template editing is permission-gated by `email_template.edit`; do not rely on template-only hiding.
- Default templates and permissions are seeded through migrations and role seed logic. Keep them idempotent.
- Preserve German user-facing labels/messages unless a template is intentionally language-specific.

## Checks

- Run `python manage.py test apps.email_templates` after changing models, forms, views, sanitization, permissions, or seed defaults.
- Permission changes must stay aligned with `ROLES_PERMISSIONS_MATRIX.md`.
