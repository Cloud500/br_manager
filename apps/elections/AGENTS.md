# AGENTS.md

## Scope

This app owns elections, candidates, candidate formsets, publication state, election permissions, and election CRUD views.

## Rules

- Candidate validation, ordering, and publication checks must be enforced server-side.
- Published-state behavior is workflow logic; do not bypass it in views or forms without tests.
- Election access is permission-gated through the app mixins; template-level hiding is not sufficient.
- Keep election behavior aligned with committee membership and role permissions.

## Checks

- Run `python manage.py test apps.elections` after election workflow, candidate, formset, or permission changes.
- Permission changes must stay aligned with `ROLES_PERMISSIONS_MATRIX.md`.
