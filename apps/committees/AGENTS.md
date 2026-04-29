# AGENTS.md

## Scope

This app owns committees, memberships, committee-scoped permissions, soft delete, substitute/external-member behavior, and Betriebsausschuss automation.

## Core Models

- `Committee` represents `MAIN`, `COMMITTEE` (Betriebsausschuss), `SUBCOMMITTEE`, and `ADHOC` bodies.
- `Membership` links users to committees with roles, member types, dates, election metadata, and active/deleted state.
- `Committee.objects` returns non-deleted committees through `SoftDeleteManager`.
- Use `Committee.all_objects` only when deleted records are intentionally needed.

## Business Rules

- `MAIN` committees must not have a parent.
- Non-`MAIN` committees must have a parent.
- Circular committee hierarchies are invalid.
- Minority-gender settings must stay internally consistent and cannot exceed total seats.
- Soft delete committees and memberships unless hard delete is explicitly required.
- External members have special constraints and should not be treated like regular voting members.

## Betriebsausschuss Rules

- Betriebsausschuss behavior is legally sensitive and tied to § 27 BetrVG.
- A `COMMITTEE` must be directly under a `MAIN` committee.
- A `COMMITTEE` always has `can_create_resolutions = True`.
- BRs with at least 9 members may trigger Betriebsausschuss creation and size validation.
- `auto_include_in_ba` roles from `apps.roles` drive automatic BA membership.
- Signals in `signals.py` auto-create/sync BA data; check them before changing `save`, `delete`, or membership commands.

## Permissions

- `CommitteePermissionMixin` checks permissions through active memberships and role permissions.
- `committee.view_all` grants broad visibility; do not add it to normal roles casually.
- Querysets in views should respect membership scope unless the user has broad permissions.

## Commands And Tests

- Management commands include committee seeding, permission assignment, and BA sync. Keep them idempotent.
- Model, permission, and view changes should be tested under `apps/committees/tests/`.
- Run `python manage.py test apps.committees` after changes here.
