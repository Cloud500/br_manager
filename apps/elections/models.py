"""Models for elections app."""

from django.core.exceptions import ValidationError
from django.db import models

from apps.agendas.models import AgendaItem


class Election(AgendaItem):
    """
    Election agenda item.

    Represents the preparation data for a person election as a dedicated
    agenda item. Conducting the vote, recording results, and election rounds
    are intentionally out of scope for this model.
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
    STATUS_CHOICES = [
        (STATUS_DRAFT, 'Entwurf'),
        (STATUS_PUBLISHED, 'Veröffentlicht'),
    ]

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
    parent_regular = models.ForeignKey(
        'agendas.AgendaItemRegular',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='election_children',
        verbose_name='Übergeordneter regulärer TOP',
        help_text='Ermöglicht Wahlen als Unter-TOP regulärer Tagesordnungspunkte'
    )

    class Meta:
        verbose_name = 'Wahl'
        verbose_name_plural = 'Wahlen'
        ordering = ['agenda', 'sort_order']
        indexes = [
            models.Index(fields=['agenda', 'status']),
            models.Index(fields=['status']),
        ]

    def clean(self) -> None:
        """Validate election data."""
        super().clean()

        if self.status == self.STATUS_PUBLISHED and not self.pk:
            raise ValidationError({
                'status': 'Eine veröffentlichte Wahl muss zuerst als Entwurf mit Kandidierenden angelegt werden.'
            })

        if self.status == self.STATUS_PUBLISHED and self.pk:
            if not self.candidates.exists():
                raise ValidationError({
                    'status': 'Eine Wahl kann nur mit mindestens einer kandidierenden Person veröffentlicht werden.'
                })

        if self.parent_id and self.parent_regular_id:
            raise ValidationError('Eine Wahl kann nur einem übergeordneten TOP zugeordnet werden.')

        if self.parent_regular_id and self.parent_regular.agenda_id != self.agenda_id:
            raise ValidationError('Der übergeordnete TOP muss zur gleichen Tagesordnung gehören.')

    def save(self, *args, **kwargs) -> None:
        """Save election while preserving published elections as read-only."""
        if not self._state.adding:
            original = Election.objects.get(pk=self.pk)
            if original.status == self.STATUS_PUBLISHED and self._has_changed_since_publish(original):
                raise ValidationError('Veröffentlichte Wahlen können nicht mehr bearbeitet werden.')

        if not self.item_type:
            self.item_type = self.__class__.__name__
        self.full_clean()

        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """Delete election unless it has already been published."""
        if self.status == self.STATUS_PUBLISHED:
            raise ValidationError('Veröffentlichte Wahlen können nicht gelöscht werden.')
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
        """Check if persisted fields changed after publication."""
        fields = [
            'agenda_id',
            'parent_id',
            'parent_regular_id',
            'title',
            'description',
            'sort_order',
            'election_type',
            'majority_type',
            'status',
        ]
        return any(getattr(self, field) != getattr(original, field) for field in fields)


class ElectionCandidate(models.Model):
    """Freitext-Kandidatur for an election."""

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
