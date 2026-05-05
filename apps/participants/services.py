"""Services for meeting participant workflows."""

from __future__ import annotations

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.mail import EmailMultiAlternatives
from django.db import transaction
from django.db.models import Max, Q
from django.db.models import QuerySet
from django.utils import timezone

from apps.committees.models import Membership
from apps.email_templates.models import EmailTemplate, RenderedEmail
from apps.meetings.models import Meeting
from apps.participants.models import MeetingParticipant


class ParticipantAction:
    """Internal action labels for service notes after history removal."""

    ACTION_CREATED = "CREATED"
    ACTION_INVITED = "INVITED"
    ACTION_ABSENCE_MARKED = "ABSENCE_MARKED"
    ACTION_SUBSTITUTE_PROPOSED = "SUBSTITUTE_PROPOSED"
    ACTION_REPLACED = "REPLACED"
    ACTION_CANCELLED = "CANCELLED"
    ACTION_REACTIVATED = "REACTIVATED"


def participant_snapshot(participant: MeetingParticipant) -> dict:
    """Return auditable participant state."""
    return {
        "status": participant.status,
        "absence_reason": participant.absence_reason,
        "nachladefaehig": participant.nachladefaehig,
        "substitute_membership_id": (
            str(participant.substitute_membership_id)
            if participant.substitute_membership_id
            else ""
        ),
        "invite_sent_at": participant.invite_sent_at.isoformat() if participant.invite_sent_at else "",
        "last_notified_at": participant.last_notified_at.isoformat() if participant.last_notified_at else "",
    }


def log_participant_change(
    participant: MeetingParticipant,
    action: str,
    old_state: dict | None = None,
    note: str = "",
    changed_by=None,
) -> None:
    """Keep service call sites explicit without persisting a history."""
    return None


def initialize_meeting_participants(meeting: Meeting) -> int:
    """Create initial participants for active regular and external members."""
    memberships = _initial_memberships(meeting)
    created_count = 0

    for membership in memberships:
        participant, created = MeetingParticipant.objects.get_or_create(
            meeting=meeting,
            membership=membership,
            defaults={
                "participant_type": MeetingParticipant._participant_type_for_membership(
                    membership
                ),
            },
        )
        if created:
            created_count += 1
            log_participant_change(
                participant,
                ParticipantAction.ACTION_CREATED,
                note="Teilnehmer wurde beim Anlegen der Sitzung initial erzeugt.",
                changed_by=meeting.created_by,
            )

    return created_count


@transaction.atomic
def add_participant(
    meeting: Meeting,
    membership: Membership,
    changed_by=None,
) -> MeetingParticipant:
    """Add an additional participant to a meeting."""
    _validate_additional_membership(meeting, membership)
    participant, created = MeetingParticipant.objects.get_or_create(
        meeting=meeting,
        membership=membership,
        defaults={
            "participant_type": MeetingParticipant._participant_type_for_membership(
                membership
            ),
            "is_initially_invited": False,
        },
    )
    if not created and participant.status == MeetingParticipant.STATUS_CANCELLED:
        old_state = participant_snapshot(participant)
        participant.status = MeetingParticipant.STATUS_CREATED
        participant.is_initially_invited = False
        participant.save(update_fields=["status", "is_initially_invited", "updated_at"])
        log_participant_change(
            participant,
            ParticipantAction.ACTION_REACTIVATED,
            old_state=old_state,
            note="Teilnehmer wurde erneut zur Sitzung hinzugefügt.",
            changed_by=changed_by,
        )
    elif created:
        log_participant_change(
            participant,
            ParticipantAction.ACTION_CREATED,
            note="Teilnehmer wurde manuell zur Sitzung hinzugefügt.",
            changed_by=changed_by,
        )

    if _meeting_invitations_are_active(meeting) and participant.is_active_for_invitation:
        send_agenda_mail(participant)

    return participant


def _validate_additional_membership(meeting: Meeting, membership: Membership) -> None:
    """Validate that a membership can be added as participant."""
    if not membership:
        raise ValidationError("Bitte eine Mitgliedschaft auswählen.")
    if not membership.is_active or membership.deleted_at:
        raise ValidationError("Die ausgewählte Mitgliedschaft ist nicht aktiv.")
    if membership.committee_id not in related_committee_ids(meeting):
        raise ValidationError("Die ausgewählte Mitgliedschaft gehört nicht zum zulässigen Gremienkreis.")
    already_invited_user = MeetingParticipant.objects.filter(
        meeting=meeting,
    ).exclude(
        status=MeetingParticipant.STATUS_CANCELLED,
    ).filter(
        Q(membership__user_id=membership.user_id)
        | Q(substitute_membership__user_id=membership.user_id)
    ).exists()
    if already_invited_user:
        raise ValidationError("Diese Person ist für diese Sitzung bereits eingeplant.")


def related_committee_ids(meeting: Meeting) -> list:
    """Return committee IDs eligible for additional participants."""
    committee = meeting.committee
    root_committee_id = committee.id if committee.committee_type == "MAIN" else committee.parent_id
    if not root_committee_id:
        return [committee.id]
    from apps.committees.models import Committee

    return list(
        Committee.objects.filter(
            Q(id=root_committee_id) | Q(parent_id=root_committee_id),
            is_active=True,
            deleted_at__isnull=True,
        ).values_list("id", flat=True)
    )


def _initial_memberships(meeting: Meeting) -> QuerySet[Membership]:
    """Return memberships that should become initial participants."""
    return Membership.objects.filter(
        committee=meeting.committee,
        is_active=True,
        deleted_at__isnull=True,
        member_type__in=["REGULAR", "EXTERNAL"],
    ).select_related("user", "role").order_by(
        "role__sort_order",
        "user__last_name",
        "user__first_name",
    )


def suggest_substitute(
    meeting: Meeting,
    excluded_participant: MeetingParticipant | None = None,
) -> Membership | None:
    """Return the next legal substitute using committee replacement logic."""
    if not excluded_participant:
        substitutes = _available_substitute_queryset(meeting)
        return substitutes.order_by(
            "election_list_position",
            "-election_votes",
            "user__last_name",
            "user__first_name",
        ).first()

    membership = excluded_participant.membership
    substitutes = list(_available_substitute_queryset(meeting, excluded_participant).filter(
        election_list_name=membership.election_list_name,
    ).exclude(
        user=membership.user,
    ))
    if not substitutes:
        return None

    current_max_position = _current_max_position_for_list(membership)
    eligible_substitutes = [
        substitute for substitute in substitutes
        if substitute.election_list_position
        and substitute.election_list_position > current_max_position
    ]
    if not eligible_substitutes:
        eligible_substitutes = substitutes

    minority_substitute = _minority_substitute_if_required(
        meeting,
        membership,
        eligible_substitutes,
    )
    if minority_substitute:
        return minority_substitute

    eligible_substitutes.sort(key=_substitute_sort_key)
    return eligible_substitutes[0] if eligible_substitutes else None


def available_substitutes_for_participant(
    participant: MeetingParticipant,
) -> list[Membership]:
    """Return selectable substitute memberships in fair rotation order."""
    all_substitutes = list(_available_substitute_queryset(
        participant.meeting,
        participant,
    ))
    if not all_substitutes:
        return []

    lists_data = {}
    for substitute in all_substitutes:
        list_name = substitute.election_list_name or "Ohne Liste"
        lists_data.setdefault(list_name, {
            "members": [],
            "current_max_position": 0,
        })["members"].append(substitute)

    for data in lists_data.values():
        data["members"].sort(key=_substitute_sort_key)

    current_members = Membership.objects.filter(
        committee=participant.meeting.committee,
        member_type="REGULAR",
        is_active=True,
        deleted_at__isnull=True,
    ).exclude(
        user=participant.membership.user,
    )
    for membership in current_members:
        list_name = membership.election_list_name or "Ohne Liste"
        if list_name in lists_data and membership.election_list_position:
            lists_data[list_name]["current_max_position"] = max(
                lists_data[list_name]["current_max_position"],
                membership.election_list_position,
            )

    sorted_substitutes = []
    list_names = sorted(lists_data.keys())
    list_indices = {name: 0 for name in list_names}
    while len(sorted_substitutes) < len(all_substitutes):
        added_in_round = False
        for list_name in list_names:
            data = lists_data[list_name]
            idx = list_indices[list_name]
            while idx < len(data["members"]):
                substitute = data["members"][idx]
                if (
                    substitute.election_list_position
                    and substitute.election_list_position > data["current_max_position"]
                ):
                    sorted_substitutes.append(substitute)
                    list_indices[list_name] = idx + 1
                    added_in_round = True
                    break
                idx += 1
                list_indices[list_name] = idx
        if not added_in_round:
            break

    remaining = [
        substitute for substitute in all_substitutes
        if substitute not in sorted_substitutes
    ]
    sorted_substitutes.extend(sorted(remaining, key=lambda item: item.user.last_name))
    return sorted_substitutes


def _available_substitute_queryset(
    meeting: Meeting,
    participant: MeetingParticipant | None = None,
) -> QuerySet[Membership]:
    """Return available substitute queryset excluding already planned participants."""
    used_membership_ids = MeetingParticipant.objects.filter(
        meeting=meeting,
        membership_id__isnull=False,
    ).exclude(
        status=MeetingParticipant.STATUS_CANCELLED,
    ).values_list("membership_id", flat=True)
    used_substitute_ids = MeetingParticipant.objects.filter(
        meeting=meeting,
        substitute_membership_id__isnull=False,
    ).exclude(
        status=MeetingParticipant.STATUS_CANCELLED,
    ).values_list("substitute_membership_id", flat=True)

    substitutes = Membership.objects.filter(
        committee=meeting.committee,
        is_active=True,
        deleted_at__isnull=True,
        member_type="SUBSTITUTE",
    ).exclude(
        id__in=used_membership_ids,
    ).exclude(
        id__in=used_substitute_ids,
    )

    if participant and participant.substitute_membership_id:
        substitutes = substitutes | Membership.objects.filter(
            id=participant.substitute_membership_id,
        )

    return substitutes.select_related("user", "role")


def _current_max_position_for_list(membership: Membership) -> int:
    """Return highest active regular position in the same list excluding membership."""
    result = Membership.objects.filter(
        committee=membership.committee,
        member_type="REGULAR",
        is_active=True,
        deleted_at__isnull=True,
        election_list_name=membership.election_list_name,
    ).exclude(
        user=membership.user,
    ).aggregate(max_pos=Max("election_list_position"))
    return result.get("max_pos") or 0


def _minority_substitute_if_required(
    meeting: Meeting,
    membership: Membership,
    substitutes: list[Membership],
) -> Membership | None:
    """Return minority-gender substitute when the BetrVG quota is not met."""
    committee = meeting.committee
    if not committee.minority_gender or not committee.minority_min_count:
        return None

    current_minority_count = Membership.objects.filter(
        committee=committee,
        member_type="REGULAR",
        is_active=True,
        deleted_at__isnull=True,
        user__gender=committee.minority_gender,
    ).exclude(
        user=membership.user,
    ).count()
    if current_minority_count >= committee.minority_min_count:
        return None

    minority_substitutes = [
        substitute for substitute in substitutes
        if substitute.user.gender == committee.minority_gender
    ]
    minority_substitutes.sort(key=_substitute_sort_key)
    return minority_substitutes[0] if minority_substitutes else None


def _substitute_sort_key(membership: Membership) -> tuple:
    """Return substitute ordering key matching committee replacement."""
    return (
        membership.election_list_position if membership.election_list_position else float("inf"),
        -(membership.election_votes if membership.election_votes else 0),
        membership.user.last_name,
        membership.user.first_name,
    )


@transaction.atomic
def mark_absent(
    participant: MeetingParticipant,
    absence_reason: str,
    nachladefaehig: bool,
    substitute_membership: Membership | None = None,
    changed_by=None,
) -> Membership | None:
    """Mark absence and optionally apply a meeting-scoped substitute."""
    if participant.status in [
        MeetingParticipant.STATUS_CANCELLED,
    ]:
        raise ValidationError("Dieser Teilnehmer kann nicht abwesend gesetzt werden.")

    original_status = participant.status
    old_state = participant_snapshot(participant)
    previous_substitute = participant.substitute_membership
    participant.absence_reason = absence_reason
    participant.nachladefaehig = nachladefaehig
    participant.status = MeetingParticipant.STATUS_SUBSTITUTE_PROPOSED if nachladefaehig else MeetingParticipant.STATUS_ABSENT

    log_participant_change(
        participant,
        ParticipantAction.ACTION_ABSENCE_MARKED,
        old_state=old_state,
        note=absence_reason,
        changed_by=changed_by,
    )

    if not nachladefaehig:
        _notify_previous_substitute_removed(
            participant,
            previous_substitute,
            changed_by=changed_by,
            note="Nachladefähigkeit wurde entfernt.",
        )
        participant.substitute_membership = None
        participant.status = MeetingParticipant.STATUS_ABSENT
        participant.save(update_fields=[
            "absence_reason",
            "nachladefaehig",
            "substitute_membership",
            "status",
            "updated_at",
        ])
        return None

    substitute = suggest_substitute(participant.meeting, participant)
    log_participant_change(
        participant,
        ParticipantAction.ACTION_SUBSTITUTE_PROPOSED,
        old_state=participant_snapshot(participant),
        note=_substitute_note(substitute),
        changed_by=changed_by,
    )

    if substitute_membership:
        confirmed_substitute = confirm_substitute(
            participant,
            substitute_membership,
            previous_substitute=previous_substitute,
            previous_participant_status=original_status,
            changed_by=changed_by,
        )
        return confirmed_substitute

    if previous_substitute:
        participant.substitute_membership = previous_substitute
        participant.status = MeetingParticipant.STATUS_ABSENT
        participant.save(update_fields=[
            "absence_reason",
            "nachladefaehig",
            "substitute_membership",
            "status",
            "updated_at",
        ])
        return previous_substitute

    participant.substitute_membership = None
    participant.status = MeetingParticipant.STATUS_SUBSTITUTE_PROPOSED
    participant.save(update_fields=[
        "absence_reason",
        "nachladefaehig",
        "substitute_membership",
        "status",
        "updated_at",
    ])

    return substitute


@transaction.atomic
def remove_absence(
    participant: MeetingParticipant,
    changed_by=None,
) -> None:
    """Remove an absence without a selected substitute and restore the participant."""
    if participant.substitute_membership_id:
        raise ValidationError("Bitte entfernen Sie zuerst das Ersatzmitglied.")
    if participant.status not in [
        MeetingParticipant.STATUS_ABSENT,
        MeetingParticipant.STATUS_SUBSTITUTE_PROPOSED,
    ]:
        return

    old_state = participant_snapshot(participant)
    participant.absence_reason = ""
    participant.nachladefaehig = True
    participant.status = (
        MeetingParticipant.STATUS_INVITED
        if participant.meeting.sent_at or participant.invite_sent_at
        else MeetingParticipant.STATUS_CREATED
    )
    participant.save(update_fields=[
        "absence_reason",
        "nachladefaehig",
        "status",
        "updated_at",
    ])
    log_participant_change(
        participant,
        ParticipantAction.ACTION_REACTIVATED,
        old_state=old_state,
        note="Abwesenheit wurde entfernt.",
        changed_by=changed_by,
    )
    if _meeting_invitations_are_active(participant.meeting):
        send_agenda_mail(participant)


@transaction.atomic
def remove_substitute(
    participant: MeetingParticipant,
    changed_by=None,
) -> None:
    """Remove the selected substitute and restore the original participant."""
    if not participant.substitute_membership_id:
        return

    participant.substitute_membership = None
    participant.absence_reason = ""
    participant.nachladefaehig = True
    participant.status = (
        MeetingParticipant.STATUS_INVITED
        if participant.meeting.sent_at or participant.invite_sent_at
        else MeetingParticipant.STATUS_CREATED
    )
    participant.save(update_fields=[
        "substitute_membership",
        "absence_reason",
        "nachladefaehig",
        "status",
        "updated_at",
    ])
    if _meeting_invitations_are_active(participant.meeting):
        send_agenda_mail(participant)


@transaction.atomic
def confirm_substitute(
    participant: MeetingParticipant,
    substitute_membership: Membership,
    previous_substitute: Membership | None = None,
    previous_participant_status: str | None = None,
    changed_by=None,
) -> Membership:
    """Confirm a substitute on the existing participant row only."""
    if participant.substitute_membership_id == substitute_membership.id:
        participant.status = MeetingParticipant.STATUS_ABSENT
        participant.nachladefaehig = True
        participant.save(update_fields=[
            "absence_reason",
            "status",
            "nachladefaehig",
            "updated_at",
        ])
        return substitute_membership

    if participant.status not in [
        MeetingParticipant.STATUS_SUBSTITUTE_PROPOSED,
        MeetingParticipant.STATUS_ABSENT,
    ]:
        raise ValidationError("Ersatz kann nur für nachladefähige Abwesenheiten bestätigt werden.")

    previous_substitute = previous_substitute or participant.substitute_membership
    _validate_substitute_membership(
        participant.meeting,
        substitute_membership,
        allowed_membership=previous_substitute,
    )

    old_participant_state = participant_snapshot(participant)
    participant.status = MeetingParticipant.STATUS_ABSENT
    participant.nachladefaehig = True
    participant.substitute_membership = substitute_membership
    participant.save(update_fields=[
        "absence_reason",
        "status",
        "nachladefaehig",
        "substitute_membership",
        "updated_at",
    ])

    unchanged_replacement = (
        previous_substitute
        and previous_substitute.pk == substitute_membership.pk
    )

    if previous_substitute and previous_substitute.pk != substitute_membership.pk:
        _notify_previous_substitute_removed(
            participant,
            previous_substitute,
            changed_by=changed_by,
            note=f"Ersatz wurde auf {substitute_membership.user.get_full_name()} geändert.",
        )

    log_participant_change(
        participant,
        ParticipantAction.ACTION_REPLACED,
        old_state=old_participant_state,
        note=f"Nachgeladen: {substitute_membership.user.get_full_name()}.",
        changed_by=changed_by,
    )

    if _meeting_invitations_are_active(participant.meeting) and not unchanged_replacement:
        send_agenda_mail(participant)

    return substitute_membership


def send_meeting_invitations(meeting: Meeting, message: str = "") -> int:
    """Send agenda mail to all active meeting participants."""
    recipients = meeting.participants.filter(
        Q(status__in=MeetingParticipant.ACTIVE_STATUSES)
        | Q(
            status=MeetingParticipant.STATUS_ABSENT,
            nachladefaehig=True,
            substitute_membership__isnull=False,
        )
    )
    sent_count = 0
    for participant in recipients:
        send_agenda_mail(participant, message)
        sent_count += 1
    return sent_count


def _validate_substitute_membership(
    meeting: Meeting,
    substitute_membership: Membership,
    allowed_membership: Membership | None = None,
) -> None:
    """Validate a substitute membership for this meeting."""
    if substitute_membership.committee_id != meeting.committee_id:
        raise ValidationError("Ersatzmitglied gehört nicht zum Gremium der Sitzung.")
    if not substitute_membership.is_active or substitute_membership.deleted_at:
        raise ValidationError("Ersatzmitglied ist nicht aktiv.")
    if substitute_membership.member_type != "SUBSTITUTE":
        raise ValidationError("Ausgewählte Person ist kein Ersatzmitglied.")

    already_used = MeetingParticipant.objects.filter(meeting=meeting).filter(
        Q(membership=substitute_membership)
        | Q(substitute_membership=substitute_membership)
    ).exclude(status=MeetingParticipant.STATUS_CANCELLED).exists()
    if allowed_membership and allowed_membership.id == substitute_membership.id:
        already_used = False
    if already_used:
        raise ValidationError("Ersatzmitglied ist für diese Sitzung bereits eingeplant.")


def _notify_previous_substitute_removed(
    participant: MeetingParticipant,
    replacement: Membership | None,
    note: str,
    changed_by=None,
) -> None:
    """Notify an outdated substitute without creating a stale participant row."""
    if not replacement:
        return
    log_participant_change(
        participant,
        ParticipantAction.ACTION_CANCELLED,
        old_state=participant_snapshot(participant),
        note=note,
        changed_by=changed_by,
    )
    return


def send_agenda_mail(participant: MeetingParticipant, message: str = "") -> None:
    """Send agenda invitation mail to one participant."""
    rendered_email = _agenda_email(participant, message)
    email = EmailMultiAlternatives(
        subject=rendered_email.subject,
        body=rendered_email.body_text,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[_delivery_email(participant)],
    )
    if rendered_email.body_html:
        email.attach_alternative(rendered_email.body_html, "text/html")
    email.send(fail_silently=False)
    now = timezone.now()
    replacement_delivery = bool(
        participant.status == MeetingParticipant.STATUS_ABSENT
        and participant.substitute_membership_id
    )
    if not replacement_delivery:
        participant.status = MeetingParticipant.STATUS_INVITED
    participant.invite_sent_at = participant.invite_sent_at or now
    participant.last_notified_at = now
    update_fields = ["invite_sent_at", "last_notified_at", "updated_at"]
    if not replacement_delivery:
        update_fields.append("status")
    participant.save(update_fields=update_fields)
    log_participant_change(
        participant,
        ParticipantAction.ACTION_INVITED,
        note="Agenda-Einladung wurde versendet.",
    )


def _agenda_email(participant: MeetingParticipant, message: str) -> RenderedEmail:
    """Render the configured agenda invitation e-mail."""
    meeting = participant.meeting
    template = EmailTemplate.get_default(EmailTemplate.MEETING_INVITATION)
    return template.render({
        "additional_message_block": _additional_message_block(message),
        "agenda_text": _formatted_agenda_text(participant),
        "committee_name": meeting.committee.name,
        "meeting_date": f"{meeting.date:%d.%m.%Y}",
        "meeting_location": meeting.get_full_location,
        "meeting_start_time": f"{meeting.start_time:%H:%M}",
        "meeting_title": meeting.title,
        "message": message,
        "recipient_email": _delivery_email(participant),
        "recipient_name": _delivery_name(participant),
    })


def _additional_message_block(message: str) -> str:
    """Return the optional additional message block."""
    if not message:
        return ""
    return f"\n\nZusätzliche Nachricht:\n{message}"


def _agenda_message(participant: MeetingParticipant, message: str) -> str:
    """Build agenda invitation text."""
    return _agenda_email(participant, message).body_text


def _formatted_agenda_text(participant: MeetingParticipant) -> str:
    """Return the meeting agenda as preformatted plain text for e-mails."""
    meeting = participant.meeting
    if not meeting.has_agenda:
        return ""

    agenda_lines = ["", "", "Tagesordnung:"]
    items = [
        item for item in meeting.agenda.all_items
        if _agenda_item_visible_to_participant(item, participant)
    ]
    if not items:
        agenda_lines.append("Keine sichtbaren Tagesordnungspunkte erfasst.")
        return "\n".join(agenda_lines)

    for item in items:
        agenda_lines.append(f"{item.item_number}. {item.title}")
        if item.description:
            for description_line in item.description.splitlines():
                agenda_lines.append(f"   {description_line}")

    return "\n".join(agenda_lines)


def _meeting_invitations_are_active(meeting: Meeting) -> bool:
    """Return whether participant changes should trigger invitation emails."""
    return bool(meeting.sent_at and meeting.status != 'DRAFT')


def _agenda_item_visible_to_participant(item, participant: MeetingParticipant) -> bool:
    """Return whether an agenda item may be included for this participant."""
    if item.item_type == 'REGULAR':
        return True
    if item.item_type == 'ELECTION':
        membership = _delivery_membership(participant)
        return bool(
            membership
            and _membership_has_meeting_permission(
                membership,
                item.agenda.meeting,
                'election.view',
            )
        )
    if item.item_type == 'RESOLUTION':
        try:
            resolution = item.resolution_agenda_item.resolution
        except Exception:
            return False
        membership = _delivery_membership(participant)
        return bool(
            membership
            and membership.committee_id == resolution.committee_id
            and _membership_has_permission(membership, 'resolution.view')
        )
    return False


def _delivery_membership(participant: MeetingParticipant) -> Membership | None:
    """Return the membership receiving the invitation."""
    if participant.status == MeetingParticipant.STATUS_ABSENT and participant.substitute_membership_id:
        return participant.substitute_membership
    return participant.membership


def _membership_has_meeting_permission(membership: Membership, meeting: Meeting, codename: str) -> bool:
    """Return whether a membership can use a permission for a meeting."""
    if not _membership_has_permission(membership, codename):
        return False
    if membership.committee_id == meeting.committee_id:
        return True
    return bool(
        meeting.committee.committee_type == 'MAIN'
        and membership.committee.parent_id == meeting.committee_id
        and membership.committee.committee_type == 'COMMITTEE'
    )


def _membership_has_permission(membership: Membership, codename: str) -> bool:
    """Return whether a membership role contains the given permission."""
    return bool(
        membership.role
        and membership.role.permissions.filter(codename=codename).exists()
    )


def _substitute_note(substitute: Membership | None) -> str:
    """Return a human-readable substitute suggestion note."""
    if not substitute:
        return "Kein Ersatzmitglied verfügbar."
    return f"Vorgeschlagen: {substitute.user.get_full_name()}"


def _delivery_name(participant: MeetingParticipant) -> str:
    """Return the actual invitation recipient name."""
    if participant.status == MeetingParticipant.STATUS_ABSENT and participant.substitute_membership_id:
        return participant.substitute_membership.user.get_full_name()
    return participant.display_name_for_display


def _delivery_email(participant: MeetingParticipant) -> str:
    """Return the actual invitation recipient email."""
    if participant.status == MeetingParticipant.STATUS_ABSENT and participant.substitute_membership_id:
        return _membership_email(participant.substitute_membership)
    return participant.email_for_delivery


def _membership_email(membership: Membership | None) -> str:
    """Return a membership user's email address."""
    return membership.user.email if membership and membership.user_id else ""
