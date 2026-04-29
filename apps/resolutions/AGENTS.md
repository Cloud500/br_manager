# AGENTS.md

## Scope

This app owns resolutions: drafts, proposed resolutions, approval/rejection, vote fields, resolution numbering, and resolution permissions.

## Workflow Rules

- Resolution statuses are `DRAFT`, `PROPOSED`, `APPROVED`, and `REJECTED`.
- `resolution_number` is generated when a resolution is approved or rejected.
- Number format is date-based: `YYYYMMDD-XXX`.
- `decided_at` should be set when a resolution becomes approved or rejected.
- Approved/rejected resolutions are not normal editable drafts.

## Domain Rules

- Quorum and voting fields are legally relevant and should not be treated as cosmetic fields.
- Betriebsausschuss resolutions must be proposed to the main committee according to existing validation.
- `propose_to_main_committee` only makes sense for committees with a parent.
- Agenda-linked resolutions can affect editability; inspect agenda relationships before changing resolution state logic.

## Permissions And Views

- Keep permission checks server-side in views/mixins.
- List/detail/create/update/delete/status-change views must handle unauthorised users explicitly.
- Do not rely on hidden buttons as the only protection.

## Checks

- Add tests for status changes, number generation, validation failures, and permission behavior when touched.
- Run `python manage.py test apps.resolutions` and affected agenda/meeting tests for cross-app changes.
