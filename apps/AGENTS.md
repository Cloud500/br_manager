# AGENTS.md

## Scope

This directory contains local Django apps. App-specific `AGENTS.md` files override or refine these rules.

## App Conventions

- Keep the conventional Django layout: `models.py`, `forms.py`, `views.py`, `urls.py`, `admin.py`, `templates/<app>/`, `static/<app>/`, `tests/`, `migrations/`.
- Existing apps use class-based views heavily; follow that pattern unless a function view is clearly simpler or already used for AJAX endpoints.
- App URLs use `app_name` and named routes. Templates should use `{% url %}` instead of hard-coded internal paths.
- Keep German model metadata (`verbose_name`, form labels, help texts, messages) for user-facing behavior.
- Avoid cross-app shortcuts that bypass models or mixins. Use explicit imports inside methods where the existing code does so to avoid circular imports.

## Domain Rules

- Permissions are custom RBAC data in `apps.roles`, not only Django's built-in auth permissions.
- Membership-scoped access usually flows through `apps.committees.models.Membership` and role permissions.
- BetrVG-related rules are part of core business logic. Do not simplify them without tests and an explicit user request.
- Soft-delete behavior exists in committees; do not replace it with hard deletes unless explicitly required.
- Signals are used for automatic agenda and Betriebsausschuss behavior. Check signal side effects before changing save/delete flows.

## Migrations And Seed Data

- Do not edit existing migrations casually after they may have been applied.
- Migrations named `9999_*` seed permissions and defaults. Keep them idempotent.
- Role/permission defaults should stay aligned with `ROLES_PERMISSIONS_MATRIX.md`.
- Management commands under `management/commands/` should be idempotent where they create seed or sync data.

## Tests

- Prefer app-local tests under `apps/<app>/tests/`.
- Keep legacy placeholder `tests.py` files untouched unless migrating tests deliberately.
- Permission and workflow changes need tests for both allowed and denied/invalid paths.
