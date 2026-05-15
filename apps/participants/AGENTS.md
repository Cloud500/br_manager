# AGENTS.md

## Scope

This app owns meeting participants, absence/substitute flows, participant status, attendance tracking, participant actions/services, participant permissions, and related signals.

## Core Models

- `MeetingParticipant`: Meeting-scoped participant snapshot linking membership to a specific meeting.
- `MeetingAttendanceEvent`: Append-only attendance events (confirmed, left, returned, marked absent).
- Participant types: `INTERNAL`, `EXTERNAL`, `SUBSTITUTE`.
- Participant status: `CREATED`, `INVITED`, `ABSENT`, `SUBSTITUTE_PROPOSED`, `CANCELLED`.
- Attendance status: `NOT_CONFIRMED`, `PRESENT`, `LEFT`, `ABSENT`.

## Domain Rules

- Each participant is backed by a `Membership` from the meeting's committee.
- Substitute members must have `member_type = "SUBSTITUTE"` in the committee membership.
- `nachladefaehig` determines whether a replacement substitute should be proposed for absent participants.
- `is_active_for_invitation` property determines whether the participant should receive meeting invitations.
- Attendance events are append-only and track confirmation method (`SELF`, `TOTP`, `RECOVERY`, `SYSTEM`).

## Service Layer

- Use `apps.participants.services` for participant workflows:
  - `participant_snapshot()`: Create auditable participant state snapshots.
  - `loaded_participant_for_user()`: Get the active participant record for a user in a meeting.
  - `attendance_periods_by_participant()`: Calculate attendance periods from events.
  - Additional service methods handle invitation, absence marking, substitute proposals, and reactivation.
- Participant mutations must go through service methods to ensure consistent state and audit trails.
- `ParticipantAction` constants define internal action labels used after participant history removal.

## Attendance Tracking

- Attendance events are immutable once created.
- Self-confirmation requires user authentication; TOTP/recovery-code confirmation provides cryptographic proof.
- `last_self_confirmed_at` and `last_written_confirmed_at` track different confirmation channels.
- Live meeting workflows may require reconfirmation; check meeting status and confirmation timestamps.

## Permissions

- Participant access is permission-gated through committee memberships and role permissions.
- Template-level hiding is insufficient; enforce permissions server-side in views and services.
- Clerk and chair roles have special permissions for participant management during live meetings.

## Integration Points

- Tightly coupled with `apps.meetings`, `apps.committees.models.Membership`, and `apps.email_templates` for invitations.
- Attendance periods are used by protocol generation in `apps.protocols`.
- Do not bypass service layer when changing participant state or attendance events.

## Checks

- Run `python manage.py test apps.participants` after participant workflow, service, model, signal, or permission changes.
- Permission changes must stay aligned with `ROLES_PERMISSIONS_MATRIX.md`.
- Test absence flows, substitute proposals, attendance tracking, and confirmation methods.
