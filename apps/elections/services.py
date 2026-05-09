"""Services for recording election results."""

from uuid import UUID

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.elections.models import Election, ElectionCandidateResult, ElectionResult
from apps.participants.services import current_voting_participants
from apps.protocols.models import ProtocolEntry
from apps.protocols.services import ProtocolDraftService


class ElectionResultService:
    """Record election results and mirror them to the meeting protocol."""

    @staticmethod
    @transaction.atomic
    def record_result(
        *,
        election: Election,
        candidate_votes: dict,
        elected_candidate_ids: set,
        is_quorate: bool,
        quorum_manually_overridden: bool = False,
        quorum_override_reason: str = "",
        invalid_votes: int = 0,
        actor=None,
    ) -> ElectionResult:
        """Persist election result and protocol mirror."""
        meeting = election.agenda.meeting
        if meeting.status != "IN_PROGRESS":
            raise ValidationError("Wahlergebnisse können nur während einer laufenden Sitzung erfasst werden.")
        if meeting.current_agenda_item_id != election.agenda_item_id:
            raise ValidationError("Wahlergebnisse können nur für den aktuell aktiven TOP erfasst werden.")
        if election.status not in [Election.STATUS_DRAFT, Election.STATUS_PUBLISHED, Election.STATUS_COMPLETED]:
            raise ValidationError("Diese Wahl kann nicht protokolliert werden.")
        if invalid_votes < 0 or any(votes < 0 for votes in candidate_votes.values()):
            raise ValidationError("Stimmen dürfen nicht negativ sein.")

        candidates = list(election.candidates.all())
        normalized_votes = ElectionResultService._normalize_candidate_votes(candidate_votes, candidates)
        elected_candidate_ids = ElectionResultService._normalize_candidate_ids(elected_candidate_ids, candidates)
        votes_cast = sum(normalized_votes.values()) + invalid_votes
        eligible_voters = current_voting_participants(meeting).count()
        if votes_cast > eligible_voters:
            raise ValidationError("Mehr Stimmen als aktuell anwesende stimmberechtigte Teilnehmer erfasst.")
        result, _created = ElectionResult.objects.update_or_create(
            election=election,
            defaults={
                "is_quorate": is_quorate,
                "quorum_manually_overridden": quorum_manually_overridden,
                "quorum_override_reason": quorum_override_reason.strip(),
                "eligible_voters": eligible_voters,
                "votes_cast": votes_cast,
                "invalid_votes": invalid_votes,
                "recorded_by": actor if getattr(actor, "is_authenticated", False) else None,
                "recorded_at": timezone.now(),
            },
        )
        result.candidate_results.all().delete()
        for candidate in candidates:
            ElectionCandidateResult.objects.create(
                result=result,
                candidate=candidate,
                votes=normalized_votes[candidate.pk],
                elected=candidate.pk in elected_candidate_ids,
            )
        if election.status != Election.STATUS_COMPLETED:
            election.status = Election.STATUS_COMPLETED
            election.save(update_fields=["status"])

        protocol = ProtocolDraftService.get_or_create_for_meeting(meeting, actor=actor)
        data = {
            "election_id": str(election.pk),
            "is_quorate": result.is_quorate,
            "quorum_manually_overridden": result.quorum_manually_overridden,
            "quorum_override_reason": result.quorum_override_reason,
            "eligible_voters": result.eligible_voters,
            "votes_cast": result.votes_cast,
            "invalid_votes": result.invalid_votes,
            "recorded_at": result.recorded_at.isoformat(),
            "candidate_results": [
                {
                    "candidate_id": str(candidate_result.candidate_id),
                    "name": candidate_result.candidate.name,
                    "votes": candidate_result.votes,
                    "elected": candidate_result.elected,
                }
                for candidate_result in result.candidate_results.select_related("candidate")
            ],
        }
        ProtocolDraftService.record_result_entry(
            protocol=protocol,
            agenda_item=election.agenda_item,
            entry_type=ProtocolEntry.ENTRY_ELECTION,
            title=election.title,
            data=data,
            object_ref=f"election:{election.pk}",
            actor=actor,
        )
        return result

    @staticmethod
    def _normalize_candidate_votes(candidate_votes: dict, candidates: list) -> dict:
        """Return candidate votes keyed by UUID and reject unknown candidate ids."""
        known_ids = {candidate.pk for candidate in candidates}
        normalized = {candidate.pk: 0 for candidate in candidates}
        for candidate_id, votes in candidate_votes.items():
            try:
                normalized_id = candidate_id if isinstance(candidate_id, UUID) else UUID(str(candidate_id))
            except (TypeError, ValueError):
                raise ValidationError("Unbekannter Wahlvorschlag in der Ergebnisliste.") from None
            if normalized_id not in known_ids:
                raise ValidationError("Unbekannter Wahlvorschlag in der Ergebnisliste.")
            normalized[normalized_id] = votes
        return normalized

    @staticmethod
    def _normalize_candidate_ids(candidate_ids: set, candidates: list) -> set:
        """Return selected candidate ids as UUIDs and reject unknown candidates."""
        known_ids = {candidate.pk for candidate in candidates}
        try:
            normalized = {
                candidate_id if isinstance(candidate_id, UUID) else UUID(str(candidate_id))
                for candidate_id in candidate_ids
            }
        except (TypeError, ValueError):
            raise ValidationError("Unbekannter gewählter Wahlvorschlag.") from None
        if not normalized.issubset(known_ids):
            raise ValidationError("Unbekannter gewählter Wahlvorschlag.")
        return normalized
