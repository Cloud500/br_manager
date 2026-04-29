# AGENTS.md

## Scope

This directory contains shared pytest fixtures and cross-app test setup. Most application tests live under `apps/<app>/tests/`.

## Fixture Rules

- `conftest.py` provides shared `user`, `admin_user`, `users`, `totp_secret`, and `totp_code` fixtures.
- Shared fixtures should stay generic. App-specific factories or fixtures belong in the relevant app test package.
- The default test users have 2FA enabled via `UserFactory`.
- Do not make shared fixtures depend on one specific app's scenario unless it is truly global.

## Test Style

- Existing app tests use Django `TestCase`; pytest fixtures are also available where pytest is used.
- Prefer clear tests for model validation, permissions, and workflows over broad snapshot-style assertions.
- For permission changes, test both an allowed and a denied user.
- For security-sensitive code, test failure paths as explicitly as success paths.

## Commands

- Full Django suite: `python manage.py test`.
- Targeted app suite: `python manage.py test apps.<app_name>`.
- Pytest suite if configured in the active environment: `pytest`.
