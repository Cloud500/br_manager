# AGENTS.md

## Scope

This app owns meeting creation, editing, deletion, invitations, start/complete actions, location validation, meeting numbers, and meeting-scoped permissions.

## Workflow Rules

- Meeting status flow is `DRAFT -> SENT -> IN_PROGRESS -> COMPLETED`.
- Draft meetings are editable/deletable; later statuses are restricted by model properties and permissions.
- Invitation sending, starting, and completing meetings must respect status and permission checks.
- Changing meeting status can affect agendas and resolution handling; inspect `apps.agendas` and `apps.resolutions` for side effects.

## Validation Rules

- `ONLINE` meetings require `location_url` and must not include address fields.
- `IN_PERSON` meetings require full address fields and must not include `location_url`.
- `HYBRID` meetings require both online URL and address fields.
- Planned and actual end times must not be before their corresponding start times.
- Chair and clerk are selected from active committee members and permission-eligible roles.

## Numbering And Permissions

- `meeting_number` is auto-generated per committee and year.
- `MeetingPermissionMixin` and `MeetingCreatePermissionMixin` enforce action-specific permissions.
- BA special-case permissions are part of existing behavior; do not remove without tests.

## UI And AJAX

- Member selection uses app-local widgets/templates and an AJAX endpoint for committee members.
- Keep server-side validation authoritative even when client-side filtering exists.

## Checks

- Run `python manage.py test apps.meetings` after workflow, validation, or permission changes.
- Include tests for every changed meeting type and status transition.
