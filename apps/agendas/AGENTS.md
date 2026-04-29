# AGENTS.md

## Scope

This app owns agendas, agenda items, TOP numbering, agenda item reordering, agenda permissions, and agenda-linked resolution items.

## Core Rules

- Each meeting has exactly one `Agenda` through a `OneToOneField`.
- `apps.agendas.signals.create_agenda_for_meeting` creates agendas automatically for new meetings.
- Agenda editability is derived from the associated meeting status.
- Finalized/editable query helpers live in `managers.py` and depend on meeting status.

## Agenda Items

- `AgendaItem` is an abstract base for concrete item types.
- `AgendaItemRegular` and `AgendaItemResolution` must remain distinguishable.
- Parent/child relationships drive hierarchical TOP numbering such as `1`, `1.1`, `1.2`, `2`.
- Reordering must update `sort_order` and then recalculate `item_number` consistently.
- Do not update only visible order in templates or JavaScript; persist order server-side.

## Permissions

- `AgendaPermissionMixin` enforces agenda permissions through committee memberships and role permissions.
- The Betriebsausschuss special rule for MAIN committees is intentional and must be tested if changed.
- Superuser/staff access is currently a guard clause; do not remove accidentally.

## Frontend

- App-local static files live under `apps/agendas/static/agendas/`.
- Drag-and-drop behavior must degrade safely: server-side reorder endpoint remains authoritative.
- Keep include templates under `templates/agendas/includes/` reusable and permission-aware.

## Checks

- Test numbering, reordering, editability, and permission changes.
- Run agenda tests and affected meeting tests after changes here.
