# AGENTS.md

## Scope

This app owns the custom role-based access control model: `Permission`, `Role`, and `RolePermission`.

## RBAC Rules

- Permission codenames use dotted names such as `meeting.create`, `committee.view_all`, and `role.assign_permissions`.
- Roles are either `SYSTEM` or `COMMITTEE` roles.
- `SYSTEM_ADMIN` is expected to receive all permissions through seed logic.
- `USER` is expected to receive no elevated permissions by default.
- Committee roles include `CHAIR`, `VICE_CHAIR`, `CLERK`, `MEMBER`, `SUBSTITUTE`, `EXTERNAL_MEMBER`, and `GUEST`.
- `RolePermission` is the through model and tracks assignment metadata; do not bypass it when metadata matters.

## Cross-App Impact

- Permission changes affect views and mixins in accounts, committees, meetings, agendas, and resolutions.
- `auto_include_in_ba` is consumed by Betriebsausschuss logic in `apps.committees`.
- Keep role/permission defaults aligned with `ROLES_PERMISSIONS_MATRIX.md`, `apps/roles/migrations/9999_seed_roles_and_permissions.py`, and app-specific permission seed migrations.

## Safety Rules

- Do not make system roles deletable unless explicitly requested.
- Do not grant broad permissions to default users as a convenience fix.
- Permission UI changes must still enforce permissions server-side in views or mixins.

## Checks

- Run role tests after RBAC changes: `python manage.py test apps.roles`.
- Also run affected app tests when changing codenames or default assignments.
