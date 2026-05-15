# AGENTS.md

## Scope

This app owns elections, candidates, candidate formsets, publication state, election permissions, and election CRUD views.

## Core Models

- `Election`: Election linked one-to-one with an `AgendaItem` of type `TYPE_ELECTION`.
- `ElectionCandidate`: Free-text candidate entries for an election (no user link).
- `ElectionResult`: Result record capturing votes, elected status, and protocol data.
- Election types: currently only `PERSON` (person election) is supported.
- Majority types: `absolute` or `relative`.
- Status flow: `DRAFT -> PUBLISHED -> COMPLETED`.

## Domain Rules

- Elections are linked to agenda items; the agenda item owns TOP hierarchy, numbering, and title/description.
- Published elections become read-only; further edits raise `ValidationError`.
- Elections require at least one candidate before publication.
- Completed elections preserve result data and cannot be edited or deleted.
- Election delete cascades through the linked agenda item.
- Candidate names are free-text strings, not linked to user accounts.

## Workflow Properties

- `is_editable`: Election can be edited if status is `DRAFT` and agenda is editable.
- `is_deletable`: Election can be deleted if status is `DRAFT` and agenda is editable.
- `is_publishable`: Election can be published if status is `DRAFT` and candidates exist.
- Use `.publish()` method to transition from `DRAFT` to `PUBLISHED`.

## Permissions

- Election access is permission-gated through committee membership and role permissions via app-specific mixins.
- Template-level hiding is not sufficient; enforce permissions server-side in views.
- Keep election behavior aligned with `ROLES_PERMISSIONS_MATRIX.md`.

## Formsets And Views

- Candidate formsets are used for inline editing of multiple candidates.
- Server-side validation ensures candidate uniqueness per election and sort order consistency.
- Publication checks must be enforced server-side in views, not only in templates.

## Checks

- Run `python manage.py test apps.elections` after election workflow, candidate, formset, or permission changes.
- Test publication validation, read-only behavior after publish, and candidate uniqueness constraints.
- Permission changes must stay aligned with `ROLES_PERMISSIONS_MATRIX.md`.
