# AGENTS.md

## Project Context

BR Manager is a Django application for German works council management. The domain is legally and security sensitive: Betriebsrat workflows, BetrVG constraints, DSGVO/privacy, authentication, role-based permissions, and auditability matter more than quick UI shortcuts.

Ignore the `docs/` directory unless the user explicitly asks to use it. Prefer the implemented code, tests, `README.md`, `ROLES_PERMISSIONS_MATRIX.md`, and configuration files as the source of truth.

## Stack

- Python 3.12+.
- Django 6.x project with app modules under `apps/`.
- Server-rendered Django templates with Bootstrap 5, Bootstrap Icons, HTMX, and small app-local static assets.
- Custom user model: `AUTH_USER_MODEL = "accounts.User"`.
- Settings split under `config/settings/`.
- Development defaults use SQLite through `config.settings.development`; production uses environment-driven PostgreSQL settings.

## Common Commands

- Run Django locally: `python manage.py runserver`.
- Run migrations: `python manage.py migrate`.
- Create migrations: `python manage.py makemigrations`.
- Run tests: `python manage.py test` or `pytest` if pytest-django is configured in the active environment.
- Run one app's tests: `python manage.py test apps.<app_name>`.
- Lint/format if available: `ruff check .`, `black .`, `isort .`.

Use the active virtual environment or `uv run <command>` if this workspace is using uv for command execution.

## Repository Rules

- Do not edit generated caches: `__pycache__/`, `.pytest_cache/`, `.ruff_cache/`, `.venv/`, `staticfiles/`.
- Do not treat `db.sqlite3`, `media/`, or local test data output as canonical application logic.
- Never print or commit secrets from `.env` files. `.env.example` is safe to inspect.
- Use `CODE_STYLE_GUIDE.md` as the style authority for new and changed code.
- Keep German user-facing text unless the existing feature is already English-only.
- Keep UUID primary-key conventions in existing domain models.
- Add or update tests close to the affected app when changing model validation, permissions, views, or workflows.
- Do not weaken security defaults for production to make local development easier; use development/test settings for that.

## Code Style

- Follow `CODE_STYLE_GUIDE.md` for formatting, naming, structure, and project-specific style rules.
- If `CODE_STYLE_GUIDE.md` conflicts with implemented code patterns, prefer the nearby implemented code unless the user explicitly asks to refactor toward the guide.
- Keep changes minimal and consistent with existing app-local style.

## Architecture Rules

- Keep domain invariants in models, managers, validators, or permission mixins rather than only in templates.
- Use class-based views where the app already uses them.
- Permissions must be enforced server-side. Template-level hiding is not sufficient.
- Status workflows are business logic. Do not add new transitions or bypass validations without tests.
- Seed migrations and management commands encode role/permission defaults. Keep them aligned with `ROLES_PERMISSIONS_MATRIX.md`.
- When changing permissions, inspect affected apps, migrations named `9999_*`, management commands, and tests.

## App Map

- `apps/accounts`: custom users, profile, invitations, 2FA, admin/staff access flows.
- `apps/roles`: custom RBAC models, system/committee roles, permission assignments.
- `apps/committees`: committees, memberships, soft delete, Betriebsausschuss and BetrVG-related membership rules.
- `apps/meetings`: meeting scheduling, location validation, status workflow, meeting permissions.
- `apps/agendas`: one agenda per meeting, agenda items, TOP numbering, reorder behavior, resolution agenda items.
- `apps/resolutions`: resolution drafts, proposals, approval/rejection, voting fields and resolution numbers.
- `apps/core`: authenticated dashboard and high-level navigation entry points.

## Testing Expectations

- Model validation changes need model tests.
- Permission changes need permission/view tests.
- View changes need tests for allowed and denied users where practical.
- Workflow changes need tests for valid and invalid status transitions.
- Avoid relying on wall-clock-sensitive TOTP assertions unless using the shared fixtures in `tests/conftest.py`.
