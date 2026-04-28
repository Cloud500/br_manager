"""Signal handlers for agendas app."""

from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.meetings.models import Meeting
from .models import Agenda


@receiver(post_save, sender=Meeting)
def create_agenda_for_meeting(sender, instance, created, **kwargs) -> None:
    """
    Create agenda automatically when a new meeting is created.
    
    Args:
        sender: Model class (Meeting)
        instance: Meeting instance
        created: Boolean indicating if this is a new instance
        **kwargs: Additional signal arguments
    """
    if created:
        Agenda.objects.create(meeting=instance)
