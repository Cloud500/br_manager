"""Services for recording legally relevant resolution results."""

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.participants.services import current_voting_participants
from apps.protocols.forms import sanitize_protocol_note_html
from apps.protocols.models import ProtocolEntry
from apps.protocols.services import ProtocolDraftService
from apps.resolutions.models import Resolution


class ResolutionDecisionService:
    """Record resolution voting results and mirror them to the protocol."""

    @staticmethod
    @transaction.atomic
    def record_result(
        *,
        resolution_agenda_item,
        yes_votes: int,
        no_votes: int,
        abstentions: int,
        is_quorate: bool,
        quorum_manually_overridden: bool = False,
        quorum_override_reason: str = "",
        decision_text: str = "",
        actor=None,
    ) -> Resolution:
        """Persist voting results on the resolution and protocol entry."""
        agenda_item = resolution_agenda_item.agenda_item
        meeting = agenda_item.agenda.meeting
        if meeting.status != "IN_PROGRESS":
            raise ValidationError(
                "Beschlussergebnisse können nur während einer laufenden Sitzung erfasst werden."
            )
        if meeting.current_agenda_item_id != agenda_item.pk:
            raise ValidationError(
                "Beschlussergebnisse können nur für den aktuell aktiven TOP erfasst werden."
            )
        if min(yes_votes, no_votes, abstentions) < 0:
            raise ValidationError("Stimmen dürfen nicht negativ sein.")
        eligible_voters = current_voting_participants(meeting).count()
        votes_cast = yes_votes + no_votes + abstentions
        if votes_cast > eligible_voters:
            raise ValidationError(
                "Mehr Stimmen als aktuell anwesende stimmberechtigte Teilnehmer erfasst."
            )

        resolution = Resolution.objects.select_for_update().get(
            pk=resolution_agenda_item.resolution_id
        )
        resolution.yes_votes = yes_votes
        resolution.no_votes = no_votes
        resolution.abstentions = abstentions
        resolution.is_quorate = is_quorate
        resolution.quorum_manually_overridden = quorum_manually_overridden
        resolution.quorum_override_reason = quorum_override_reason.strip()
        resolution.decision_text = sanitize_protocol_note_html(decision_text)
        resolution.status = (
            "APPROVED" if is_quorate and yes_votes > no_votes else "REJECTED"
        )
        resolution.decided_at = timezone.now()
        resolution.save(
            update_fields=[
                "yes_votes",
                "no_votes",
                "abstentions",
                "is_quorate",
                "quorum_manually_overridden",
                "quorum_override_reason",
                "decision_text",
                "status",
                "decided_at",
                "resolution_number",
                "updated_at",
            ]
        )

        protocol = ProtocolDraftService.get_or_create_for_meeting(meeting, actor=actor)
        data = {
            "resolution_id": str(resolution.pk),
            "resolution_number": resolution.resolution_number,
            "agenda_item_title": agenda_item.title,
            "agenda_item_description": agenda_item.description,
            "yes_votes": yes_votes,
            "no_votes": no_votes,
            "abstentions": abstentions,
            "is_quorate": is_quorate,
            "quorum_manually_overridden": quorum_manually_overridden,
            "quorum_override_reason": resolution.quorum_override_reason,
            "decision_text": resolution.decision_text,
            "status": resolution.status,
            "eligible_voters": eligible_voters,
            "decided_at": (
                resolution.decided_at.isoformat() if resolution.decided_at else ""
            ),
        }
        ProtocolDraftService.record_result_entry(
            protocol=protocol,
            agenda_item=agenda_item,
            entry_type=ProtocolEntry.ENTRY_RESOLUTION,
            title=agenda_item.title,
            data=data,
            object_ref=f"resolution:{resolution.pk}",
            actor=actor,
        )
        return resolution
