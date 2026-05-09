"""Models for elections app."""

import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from apps.agendas.models import AgendaItem


class Election(models.Model):
    """
    Election linked to a dedicated agenda item.

    The agenda item owns TOP hierarchy, numbering and title/description.
    This model owns election-specific preparation data.
    """

    ELECTION_TYPE_PERSON = 'PERSON'
    ELECTION_TYPE_CHOICES = [
        (ELECTION_TYPE_PERSON, 'Personenwahl'),
    ]

    MAJORITY_ABSOLUTE = 'absolute'
    MAJORITY_RELATIVE = 'relative'
    MAJORITY_TYPE_CHOICES = [
        (MAJORITY_ABSOLUTE, 'Absolute Mehrheit'),
        (MAJORITY_RELATIVE, 'Relative Mehrheit'),
    ]

    STATUS_DRAFT = 'DRAFT'
    STATUS_PUBLISHED = 'PUBLISHED'
    STATUS_COMPLETED = 'COMPLETED'
    STATUS_CHOICES = [
        (STATUS_DRAFT, 'Entwurf'),
        (STATUS_PUBLISHED, 'Veröffentlicht'),
        (STATUS_COMPLETED, 'Durchgeführt'),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name='ID'
    )
    agenda_item = models.OneToOneField(
        AgendaItem,
        on_delete=models.CASCADE,
        related_name='election_link',
        verbose_name='Tagesordnungspunkt'
    )
    election_type = models.CharField(
        max_length=20,
        choices=ELECTION_TYPE_CHOICES,
        default=ELECTION_TYPE_PERSON,
        verbose_name='Wahlart',
        help_text='Derzeit wird nur die Personenwahl unterstützt'
    )
    majority_type = models.CharField(
        max_length=20,
        choices=MAJORITY_TYPE_CHOICES,
        default=MAJORITY_ABSOLUTE,
        verbose_name='Mehrheitserfordernis',
        help_text='Absolute oder relative Mehrheit für die vorbereitete Wahl'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_DRAFT,
        verbose_name='Status'
    )

    class Meta:
        verbose_name = 'Wahl'
        verbose_name_plural = 'Wahlen'
        ordering = ['agenda_item__agenda', 'agenda_item__sort_order']
        indexes = [
            models.Index(fields=['status']),
        ]

    def __str__(self) -> str:
        """Return the election title."""
        return self.title

    @property
    def agenda(self):
        """Return the agenda of the linked TOP."""
        return self.agenda_item.agenda

    @property
    def title(self) -> str:
        """Return the linked TOP title."""
        return self.agenda_item.title

    @property
    def description(self) -> str:
        """Return the linked TOP description."""
        return self.agenda_item.description

    @property
    def item_number(self) -> str:
        """Return the linked TOP number."""
        return self.agenda_item.item_number

    @property
    def sort_order(self) -> float:
        """Return the linked TOP sort order."""
        return self.agenda_item.sort_order

    def clean(self) -> None:
        """Validate election data."""
        super().clean()

        if self.agenda_item_id and self.agenda_item.item_type != AgendaItem.TYPE_ELECTION:
            raise ValidationError('Eine Wahl muss mit einem Wahl-TOP verknüpft sein.')

        if self.status == self.STATUS_PUBLISHED and self._state.adding:
            raise ValidationError({
                'status': 'Eine veröffentlichte Wahl muss zuerst als Entwurf mit Kandidierenden angelegt werden.'
            })

        if self.status in [self.STATUS_PUBLISHED, self.STATUS_COMPLETED] and not self._state.adding and not self.candidates.exists():
            raise ValidationError({
                'status': 'Eine Wahl kann nur mit mindestens einer kandidierenden Person veröffentlicht werden.'
            })

    def save(self, *args, **kwargs) -> None:
        """Save election while preserving published elections as read-only."""
        if not self._state.adding:
            original = Election.objects.get(pk=self.pk)
            if original.status in [self.STATUS_PUBLISHED, self.STATUS_COMPLETED] and self._has_changed_since_publish(original):
                raise ValidationError('Veröffentlichte Wahlen können nicht mehr bearbeitet werden.')

        self.full_clean()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """Delete election by deleting its agenda item."""
        if self.status in [self.STATUS_PUBLISHED, self.STATUS_COMPLETED]:
            raise ValidationError('Veröffentlichte Wahlen können nicht gelöscht werden.')
        if self.agenda_item_id:
            return self.agenda_item.delete(*args, **kwargs)
        return super().delete(*args, **kwargs)

    def publish(self) -> None:
        """Publish the election and make it read-only."""
        if self.status == self.STATUS_PUBLISHED:
            return
        previous_status = self.status
        self.status = self.STATUS_PUBLISHED
        try:
            self.save()
        except ValidationError:
            self.status = previous_status
            raise

    @property
    def is_editable(self) -> bool:
        """Return whether the election can still be edited."""
        return self.status == self.STATUS_DRAFT and self.agenda.is_editable

    @property
    def is_deletable(self) -> bool:
        """Return whether the election can be deleted."""
        return self.status == self.STATUS_DRAFT and self.agenda.is_editable

    @property
    def is_publishable(self) -> bool:
        """Return whether the election can be published."""
        return self.status == self.STATUS_DRAFT and self.candidates.exists()

    def _has_changed_since_publish(self, original: 'Election') -> bool:
        """Check if persisted election fields changed after publication."""
        fields = ['agenda_item_id', 'election_type', 'majority_type']
        return any(getattr(self, field) != getattr(original, field) for field in fields)


class ElectionCandidate(models.Model):
    """Freitext-Kandidatur for an election."""

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name='ID'
    )
    election = models.ForeignKey(
        Election,
        on_delete=models.CASCADE,
        related_name='candidates',
        verbose_name='Wahl'
    )
    name = models.CharField(
        max_length=255,
        verbose_name='Name',
        help_text='Freitextname der kandidierenden Person; keine Benutzer-Verknüpfung'
    )
    sort_order = models.PositiveIntegerField(
        default=0,
        verbose_name='Sortierung'
    )

    class Meta:
        verbose_name = 'Kandidierende Person'
        verbose_name_plural = 'Kandidierende Personen'
        ordering = ['sort_order', 'name']
        constraints = [
            models.UniqueConstraint(
                fields=['election', 'name'],
                name='unique_candidate_name_per_election'
            ),
        ]

    def __str__(self) -> str:
        """String representation."""
        return self.name

    def clean(self) -> None:
        """Validate candidate data."""
        super().clean()
        if not self._state.adding:
            original = ElectionCandidate.objects.get(pk=self.pk)
            if original.election.status == Election.STATUS_PUBLISHED:
                raise ValidationError('Kandidierende Personen veröffentlichter Wahlen können nicht geändert werden.')

        if self.election_id and self.election.status == Election.STATUS_PUBLISHED:
            raise ValidationError('Kandidierende Personen veröffentlichter Wahlen können nicht geändert werden.')

    def save(self, *args, **kwargs) -> None:
        """Save candidate with model validation."""
        self.name = self.name.strip()
        self.full_clean()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """Delete candidate unless the election is published."""
        if self.election.status == Election.STATUS_PUBLISHED:
            raise ValidationError('Kandidierende Personen veröffentlichter Wahlen können nicht gelöscht werden.')
        return super().delete(*args, **kwargs)


class ElectionResult(models.Model):
    """Recorded result for a published election."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    election = models.OneToOneField(
        Election,
        on_delete=models.CASCADE,
        related_name='result',
        verbose_name='Wahl',
    )
    is_quorate = models.BooleanField(null=True, blank=True, verbose_name='Beschlussfähig')
    quorum_manually_overridden = models.BooleanField(
        default=False,
        verbose_name='Beschlussfähigkeit manuell überschrieben',
    )
    quorum_override_reason = models.TextField(blank=True, verbose_name='Begründung Quorum-Override')
    eligible_voters = models.PositiveIntegerField(default=0, verbose_name='Stimmberechtigte')
    votes_cast = models.PositiveIntegerField(default=0, verbose_name='Abgegebene Stimmen')
    invalid_votes = models.PositiveIntegerField(default=0, verbose_name='Ungültige Stimmen')
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='recorded_election_results',
        verbose_name='Erfasst von',
    )
    recorded_at = models.DateTimeField(default=timezone.now, verbose_name='Erfasst am')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Aktualisiert am')

    class Meta:
        verbose_name = 'Wahlergebnis'
        verbose_name_plural = 'Wahlergebnisse'
        ordering = ['-recorded_at']

    def __str__(self) -> str:
        """Return election result label."""
        return f'Ergebnis: {self.election.title}'


class ElectionCandidateResult(models.Model):
    """Vote count for one candidate in an election result."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    result = models.ForeignKey(
        ElectionResult,
        on_delete=models.CASCADE,
        related_name='candidate_results',
        verbose_name='Wahlergebnis',
    )
    candidate = models.ForeignKey(
        ElectionCandidate,
        on_delete=models.CASCADE,
        related_name='results',
        verbose_name='Kandidierende Person',
    )
    votes = models.PositiveIntegerField(default=0, verbose_name='Stimmen')
    elected = models.BooleanField(default=False, verbose_name='Gewählt')

    class Meta:
        verbose_name = 'Kandidierenden-Ergebnis'
        verbose_name_plural = 'Kandidierenden-Ergebnisse'
        ordering = ['candidate__sort_order', 'candidate__name']
        constraints = [
            models.UniqueConstraint(
                fields=['result', 'candidate'],
                name='unique_candidate_result_per_election_result',
            ),
        ]

    def __str__(self) -> str:
        """Return candidate result label."""
        return f'{self.candidate.name}: {self.votes}'
