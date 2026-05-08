# AGENTS.md

## Scope

This app owns meeting participants, absence/substitute flows, participant actions/services, participant permissions, and related signals.

## Rules

- Participant mutations must stay server-side and permission-gated; template controls are not enough.
- Keep participant state consistent with meeting, committee, membership, and substitute rules.
- Prefer the existing service/action abstractions for add, remove, absence, substitute, and notification-related flows.
- Preserve migrations that simplify or normalize participant data unless an explicit migration plan exists.

## Checks

- Run `python manage.py test apps.participants` after participant workflow, service, model, signal, or permission changes.
- Permission changes must stay aligned with `ROLES_PERMISSIONS_MATRIX.md`.
