# AGENTS.md

## Scope

This app owns users, profiles, invitations, login/logout, password changes, 2FA, recovery codes, admin-user flows, and test user factories.

## Invariants

- `User` is the custom auth model and logs in by unique email, not username.
- Required user fields include `first_name`, `last_name`, and `gender`.
- Gender currently supports `M` and `F` for BetrVG quota logic in related apps.
- 2FA state is stored on `User` through `two_factor_enabled`, `two_factor_method`, and `totp_secret`.
- Recovery codes are stored hashed in `TwoFactorRecoveryCode.code`; plaintext codes are only returned at generation time.
- `UserInvitation.token` is a secure token and must not be logged or exposed beyond invitation/register flows.

## Security Rules

- Never print TOTP secrets, recovery codes, invitation tokens, or password hashes in logs or responses.
- Do not lower token entropy, recovery-code hashing, or invitation expiry without explicit approval.
- Keep `Require2FAMiddleware` exemptions narrow. New auth URLs must be reviewed for 2FA bypass risk.
- Admin or permission-management users must continue to require 2FA.
- Login, registration, and 2FA flows need CSRF-protected POST handling.

## Factories And Test Data

- `UserFactory` creates German-localized users with password `testpass123` and shared development TOTP secret `DEV_TOTP_SECRET`.
- The shared development TOTP secret is for tests and local seeded users only; do not use it as production behavior.
- If changing auth behavior, update fixtures in `tests/conftest.py` only when shared behavior truly changes.

## Checks

- Auth changes should include tests under `apps/accounts/tests/`.
- Test login, 2FA setup/verify, recovery-code behavior, invitation expiry, and permission-protected user management where affected.
