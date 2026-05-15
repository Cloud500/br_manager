# AGENTS.md

## Scope

This app owns editable email templates, rendered-email helper records, template placeholder validation, HTML sanitization, plain-text extraction, template permissions, and default template seed data.

## Core Models

- `EmailTemplate`: System-provided email template editable through RBAC permissions.
- `RenderedEmail`: Frozen dataclass holding rendered subject, body_text, and body_html.
- Template types: `user_invitation` and `meeting_invitation`.
- Each template has `subject`, `body_text`, `body_html`, and `available_placeholders`.

## Domain Rules

- Placeholders use `{{ variable_name }}` syntax and are validated against `available_placeholders`.
- HTML sanitization is enforced server-side; do not trust editor/client output.
- Plain-text extraction from HTML must preserve readability for email clients without HTML support.
- Default templates are defined in `EmailTemplate.DEFAULTS` and seeded through migrations.
- Legacy body texts exist for backward compatibility during migrations.

## Template Types And Placeholders

- **user_invitation**: `invite_url`, `inviter_name`, `recipient_email`, `validity_days`.
- **meeting_invitation**: `recipient_name`, `committee_name`, `meeting_title`, `meeting_date`, `meeting_start_time`, `meeting_location`, `agenda_text`, `message`, `additional_message_block`, `recipient_email`.
- Additional template types may be added; maintain idempotent seed logic.

## Permissions

- Template editing is permission-gated by `email_template.edit`; do not rely on template-only hiding.
- Only authorized users should modify system templates; changes affect all users.
- Preserve German user-facing labels/messages unless a template is intentionally language-specific.

## Services And Rendering

- Use `EmailTemplate.render()` method to produce `RenderedEmail` instances with substituted placeholders.
- Rendering validates placeholders and escapes HTML where appropriate.
- Invalid placeholders should raise `ValidationError` during save or render.

## Seed Data And Migrations

- Default templates and permissions are seeded through migrations and role seed logic.
- Keep seed migrations idempotent; use get_or_create patterns.
- Template sort order determines display order in admin/edit interfaces.

## Checks

- Run `python manage.py test apps.email_templates` after changing models, forms, views, sanitization, permissions, or seed defaults.
- Test placeholder validation, HTML sanitization, and rendering with valid/invalid inputs.
- Permission changes must stay aligned with `ROLES_PERMISSIONS_MATRIX.md`.
