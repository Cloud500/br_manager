# AGENTS.md

## Scope

This app owns meeting protocols: protocol drafts, protocol entries, protocol notes per agenda item, protocol finalization, and protocol revision history.

## Workflow Rules

- Protocol status flow is `DRAFT -> LOCKED -> FINALIZED`.
- `DRAFT` protocols are editable by the meeting clerk and authorized users.
- `LOCKED` and `FINALIZED` protocols are immutable except through specific revision workflows (not yet implemented).
- Use `Protocol.is_editable` property to check whether regular edits are allowed.

## Model Structure

- `Protocol`: One-to-one with a meeting. Holds main protocol body text, snapshots of agenda/attendance/metadata, status, and timestamps.
- `ProtocolAgendaItemNoteForm`: Per-agenda-item clerk notes. Can be hidden from loaded participants via `visible_to_loaded_participants` flag.
- `ProtocolEntry`: Structured entries for agenda, attendance, resolution, or election data. Used for rendering final protocol sections.
- `ProtocolRevision`: Protocol-specific revision history with old/new snapshots. Separate from global audit log.

## Service Layer

- Use `ProtocolDraftService` for all protocol mutations:
  - `get_or_create_for_meeting()`: Get or create the protocol for a meeting.
  - `update_body()`: Update the main protocol text.
  - `update_item_note()`: Update or create a note for one agenda item.
  - Additional methods may exist for snapshot updates and finalization.

## Permissions And Access

- Protocol list and detail views filter by committee membership, clerk, chair, or staff privileges.
- Only the meeting clerk (or privileged users) can edit protocol drafts.
- Use `_user_can_edit_protocol_notes()` helper from `apps.meetings.views` to check clerk permissions.
- Live meeting protocol edits may require participant reconfirmation; check `_live_reconfirmation_required()` logic.

## Snapshots And Display

- `metadata_snapshot`, `attendance_snapshot`, and `agenda_snapshot` capture meeting state at protocol creation or finalization.
- Views reconstruct readable participant groups and agenda item lists from snapshots.
- Protocol entries for elections and resolutions are rendered separately from agenda notes.

## Integration Points

- Protocols are tightly coupled with `apps.meetings`, `apps.agendas`, `apps.participants`, and result-producing apps.
- Do not bypass `ProtocolDraftService` when changing protocol data; it ensures consistency and revision tracking.
- HTMX is used for live meeting protocol note updates; maintain existing response patterns.

## Checks

- Run `python manage.py test apps.protocols` after model, service, or view changes.
- Test permission boundaries: clerk vs. non-clerk, editable vs. finalized protocols.
- Verify that snapshot data is preserved correctly across status transitions.
