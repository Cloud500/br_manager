# AGENTS.md

## Scope

This directory contains Django project configuration: settings, root URLs, ASGI, and WSGI.

## Settings Rules

- Shared settings live in `config/settings/base.py`.
- Environment overrides live in `development.py`, `production.py`, and `test.py`.
- Environment parsing lives in `env_config.py` using `pydantic-settings`.
- Production settings must remain strict: HTTPS redirect, HSTS, secure cookies, and WhiteNoise storage must not be relaxed for convenience.
- Development and test settings are the correct place for local-only relaxations such as SQLite, insecure cookies, and fast password hashers.

## Security Rules

- Keep `AUTH_USER_MODEL = "accounts.User"` stable.
- Do not expose secrets, environment values, database passwords, email credentials, or secret keys in output.
- Prefer adding new typed settings to `env_config.py` instead of directly reading `os.environ` in random modules.
- Session, CSRF, cookie, host, proxy, and HSTS changes require explicit reasoning and tests or manual verification notes.

## URL Rules

- Register app URLs in `config/urls.py` with `include(..., namespace="...")` following the existing pattern.
- Keep the dashboard/root route last: `path("", include("apps.core.urls", namespace="core"))`.
- Debug toolbar and media serving must stay guarded by `settings.DEBUG`.

## Local Checks

- After changing settings or URLs, run `python manage.py check`.
- After adding an app, run `python manage.py makemigrations --check` and a targeted smoke test if possible.
