"""Signal handlers for meeting participant initialization."""

from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.meetings.models import Meeting
from apps.participants.services import initialize_meeting_participants


@receiver(post_save, sender=Meeting)
def create_initial_participants(sender, instance: Meeting, created: bool, **kwargs) -> None:
    """Create participants after a meeting was created."""
    if created:
        initialize_meeting_participants(instance)
