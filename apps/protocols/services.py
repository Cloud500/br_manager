"""Services for protocol draft generation and updates."""

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.audit.models import AuditEntry
from apps.audit.services import create_audit_entry
from apps.protocols.models import (
    Protocol,
    ProtocolAgendaItemNote,
    ProtocolEntry,
    ProtocolRevision,
)


class ProtocolDraftService:
    """Coordinate protocol draft lifecycle and audit logging."""

    @staticmethod
    def get_or_create_for_meeting(meeting, actor=None) -> Protocol:
        """Return the protocol draft for the meeting, creating it if necessary."""
        protocol, created = Protocol.objects.get_or_create(
            meeting=meeting,
            defaults={"updated_by": actor if getattr(actor, "is_authenticated", False) else None},
        )
        if created:
            ProtocolDraftService._record_revision(
                protocol=protocol,
                change_type="protocol_created",
                actor=actor,
                new_snapshot={"meeting_id": str(meeting.pk), "status": protocol.status},
            )
        return protocol

    @staticmethod
    def get_for_meeting(meeting) -> Protocol | None:
        """Return an existing protocol without creating records from read paths."""
        return Protocol.objects.filter(meeting=meeting).first()

    @staticmethod
    @transaction.atomic
    def update_item_note(protocol: Protocol, agenda_item, body: str, actor=None) -> ProtocolAgendaItemNote:
        """Create or update a clerk note for an agenda item."""
        if not protocol.is_editable:
            raise ValidationError("Finalisierte Protokolle können nicht bearbeitet werden.")
        if agenda_item.agenda.meeting_id != protocol.meeting_id:
            raise ValidationError("TOP gehört nicht zur Sitzung des Protokolls.")

        note, created = ProtocolAgendaItemNote.objects.get_or_create(
            protocol=protocol,
            agenda_item=agenda_item,
            defaults={"body": body, "updated_by": actor if getattr(actor, "is_authenticated", False) else None},
        )
        old_snapshot = {} if created else ProtocolDraftService._note_snapshot(note)
        if not created:
            note.body = body
            note.updated_by = actor if getattr(actor, "is_authenticated", False) else None
            note.save(update_fields=["body", "updated_by", "updated_at"])
        protocol.updated_by = actor if getattr(actor, "is_authenticated", False) else None
        protocol.save(update_fields=["updated_by", "updated_at"])
        ProtocolDraftService._record_revision(
            protocol=protocol,
            change_type="agenda_item_note_updated",
            actor=actor,
            object_ref=f"agenda-item:{agenda_item.pk}",
            old_snapshot=old_snapshot,
            new_snapshot=ProtocolDraftService._note_snapshot(note),
        )
        return note

    @staticmethod
    @transaction.atomic
    def update_body(protocol: Protocol, body: str, actor=None) -> Protocol:
        """Update the editable protocol body with revision/audit tracking."""
        if not protocol.is_editable:
            raise ValidationError("Finalisierte Protokolle können nicht bearbeitet werden.")
        old_snapshot = ProtocolDraftService._protocol_snapshot(protocol)
        protocol.body = body
        protocol.updated_by = actor if getattr(actor, "is_authenticated", False) else None
        protocol.save(update_fields=["body", "updated_by", "updated_at"])
        ProtocolDraftService._record_revision(
            protocol=protocol,
            change_type="protocol_body_updated",
            actor=actor,
            old_snapshot=old_snapshot,
            new_snapshot=ProtocolDraftService._protocol_snapshot(protocol),
        )
        return protocol

    @staticmethod
    def visible_notes_for_user(meeting, user) -> dict:
        """Return visible protocol notes keyed by agenda item id for loaded participants."""
        from apps.participants.services import user_is_loaded_participant

        if not user_is_loaded_participant(meeting, user) and not getattr(user, "is_staff", False):
            return {}
        protocol = ProtocolDraftService.get_for_meeting(meeting)
        if not protocol:
            return {}
        return {
            note.agenda_item_id: note
            for note in protocol.item_notes.filter(
                visible_to_loaded_participants=True,
            ).select_related("agenda_item")
        }

    @staticmethod
    @transaction.atomic
    def generate_from_meeting(meeting, actor=None) -> Protocol:
        """Refresh protocol snapshots from the meeting state."""
        protocol = ProtocolDraftService.get_or_create_for_meeting(meeting, actor=actor)
        if not protocol.is_editable:
            raise ValidationError("Finalisierte Protokolle können nicht neu erzeugt werden.")
        old_snapshot = ProtocolDraftService._protocol_snapshot(protocol)
        protocol.metadata_snapshot = ProtocolDraftService._meeting_metadata(meeting)
        protocol.attendance_snapshot = ProtocolDraftService._attendance_snapshot(meeting)
        protocol.agenda_snapshot = ProtocolDraftService._agenda_snapshot(protocol)
        protocol.updated_by = actor if getattr(actor, "is_authenticated", False) else None
        protocol.save(update_fields=[
            "metadata_snapshot",
            "attendance_snapshot",
            "agenda_snapshot",
            "updated_by",
            "updated_at",
        ])
        ProtocolDraftService._upsert_snapshot_entries(protocol)
        ProtocolDraftService._record_revision(
            protocol=protocol,
            change_type="protocol_generated",
            actor=actor,
            old_snapshot=old_snapshot,
            new_snapshot=ProtocolDraftService._protocol_snapshot(protocol),
        )
        return protocol

    @staticmethod
    @transaction.atomic
    def finalize(protocol: Protocol, actor=None) -> Protocol:
        """Finalize a protocol draft and block regular changes."""
        if protocol.status == Protocol.STATUS_FINALIZED:
            return protocol
        old_snapshot = ProtocolDraftService._protocol_snapshot(protocol)
        protocol.status = Protocol.STATUS_FINALIZED
        protocol.finalized_at = timezone.now()
        protocol.finalized_by = actor if getattr(actor, "is_authenticated", False) else None
        protocol.save(update_fields=["status", "finalized_at", "finalized_by", "updated_at"])
        ProtocolDraftService._record_revision(
            protocol=protocol,
            change_type="protocol_finalized",
            actor=actor,
            old_snapshot=old_snapshot,
            new_snapshot=ProtocolDraftService._protocol_snapshot(protocol),
            action=AuditEntry.ACTION_FINALIZED,
        )
        return protocol

    @staticmethod
    def record_result_entry(
        *,
        protocol: Protocol,
        agenda_item,
        entry_type: str,
        title: str,
        data: dict,
        object_ref: str,
        actor=None,
    ) -> ProtocolEntry:
        """Create or update the protocol mirror for a decision/election result."""
        if not protocol.is_editable:
            raise ValidationError("Finalisierte Protokolle können nicht bearbeitet werden.")
        entry, created = ProtocolEntry.objects.get_or_create(
            protocol=protocol,
            object_ref=object_ref,
            defaults={
                "agenda_item": agenda_item,
                "entry_type": entry_type,
                "title": title,
                "data": data,
            },
        )
        old_snapshot = {} if created else ProtocolDraftService._entry_snapshot(entry)
        if not created:
            entry.agenda_item = agenda_item
            entry.entry_type = entry_type
            entry.title = title
            entry.data = data
            entry.save(update_fields=["agenda_item", "entry_type", "title", "data", "updated_at"])
        ProtocolDraftService._record_revision(
            protocol=protocol,
            change_type=f"{entry_type.lower()}_result_recorded",
            actor=actor,
            object_ref=object_ref,
            old_snapshot=old_snapshot,
            new_snapshot=ProtocolDraftService._entry_snapshot(entry),
        )
        return entry

    @staticmethod
    def _meeting_metadata(meeting) -> dict:
        """Serialize meeting metadata for protocol snapshots."""
        return {
            "meeting_id": str(meeting.pk),
            "meeting_number": meeting.meeting_number,
            "title": meeting.title,
            "date": meeting.date.isoformat(),
            "start_time": meeting.start_time.isoformat() if meeting.start_time else "",
            "end_time": meeting.end_time.isoformat() if meeting.end_time else "",
            "actual_start_time": meeting.actual_start_time.isoformat() if meeting.actual_start_time else "",
            "actual_end_time": meeting.actual_end_time.isoformat() if meeting.actual_end_time else "",
            "location": meeting.get_full_location,
            "chair_id": str(meeting.chair_id) if meeting.chair_id else "",
            "clerk_id": str(meeting.clerk_id) if meeting.clerk_id else "",
        }

    @staticmethod
    def _attendance_snapshot(meeting) -> dict:
        """Serialize current participant and attendance timeline state."""
        from apps.participants.services import attendance_timeline_for_meeting

        participants = meeting.participants.select_related(
            "membership",
            "membership__user",
            "substitute_membership",
            "substitute_membership__user",
        ).order_by("membership__user__last_name", "membership__user__first_name")
        return {
            "participants": [
                {
                    "participant_id": str(participant.pk),
                    "name": participant.display_name_for_display,
                    "status": participant.status,
                    "attendance_status": participant.attendance_status,
                    "substitute_name": participant.substitute_name_for_display,
                }
                for participant in participants
            ],
            "timeline": attendance_timeline_for_meeting(meeting),
        }

    @staticmethod
    def _agenda_snapshot(protocol: Protocol) -> list[dict]:
        """Serialize agenda item state and notes."""
        if not protocol.meeting.has_agenda:
            return []
        notes = {note.agenda_item_id: note for note in protocol.item_notes.all()}
        return [
            {
                "agenda_item_id": str(item.pk),
                "item_number": item.item_number,
                "title": item.title,
                "description": item.description,
                "item_type": item.item_type,
                "note": notes[item.pk].body if item.pk in notes else "",
            }
            for item in protocol.meeting.agenda.all_items
        ]

    @staticmethod
    def _upsert_snapshot_entries(protocol: Protocol) -> None:
        """Store agenda and attendance snapshots as structured entries."""
        ProtocolEntry.objects.update_or_create(
            protocol=protocol,
            object_ref="attendance",
            defaults={
                "entry_type": ProtocolEntry.ENTRY_ATTENDANCE,
                "title": "Anwesenheit",
                "data": protocol.attendance_snapshot,
            },
        )
        for item in protocol.agenda_snapshot:
            ProtocolEntry.objects.update_or_create(
                protocol=protocol,
                object_ref=f"agenda-item:{item['agenda_item_id']}",
                defaults={
                    "entry_type": ProtocolEntry.ENTRY_AGENDA,
                    "title": item["title"],
                    "data": item,
                },
            )

    @staticmethod
    def _record_revision(
        *,
        protocol: Protocol,
        change_type: str,
        actor=None,
        object_ref: str = "",
        old_snapshot: dict | None = None,
        new_snapshot: dict | None = None,
        action: str = AuditEntry.ACTION_UPDATED,
    ) -> ProtocolRevision:
        """Write protocol revision and global audit entry."""
        revision = ProtocolRevision.objects.create(
            protocol=protocol,
            changed_by=actor if getattr(actor, "is_authenticated", False) else None,
            change_type=change_type,
            object_ref=object_ref,
            old_snapshot=old_snapshot or {},
            new_snapshot=new_snapshot or {},
        )
        create_audit_entry(
            target=protocol,
            action=action,
            change_type=change_type,
            actor=actor,
            old_snapshot=old_snapshot,
            new_snapshot=new_snapshot,
            metadata={"object_ref": object_ref, "revision_id": str(revision.pk)},
        )
        return revision

    @staticmethod
    def _note_snapshot(note: ProtocolAgendaItemNote) -> dict:
        """Serialize a protocol note."""
        return {
            "note_id": str(note.pk),
            "agenda_item_id": str(note.agenda_item_id),
            "body": note.body,
        }

    @staticmethod
    def _entry_snapshot(entry: ProtocolEntry) -> dict:
        """Serialize a protocol entry."""
        return {
            "entry_id": str(entry.pk),
            "entry_type": entry.entry_type,
            "title": entry.title,
            "data": entry.data,
            "object_ref": entry.object_ref,
        }

    @staticmethod
    def _protocol_snapshot(protocol: Protocol) -> dict:
        """Serialize protocol lifecycle state."""
        return {
            "protocol_id": str(protocol.pk),
            "status": protocol.status,
            "metadata_snapshot": protocol.metadata_snapshot,
            "attendance_snapshot": protocol.attendance_snapshot,
            "agenda_snapshot": protocol.agenda_snapshot,
        }
