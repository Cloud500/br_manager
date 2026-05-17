from django.db import models
from config.models import BaseModel


class Committee(BaseModel):
    COMMITTEE_TYPE_CHOICES = [
        ('MAIN', 'Betriebsrat (Hauptgremium)'),
        ('COMMITTEE', 'Betriebsausschuss'),
        ('SUBCOMMITTEE', 'Fachausschuss'),
        ('GROUP', 'Arbeitsgruppe'),
    ]

    name = models.CharField(max_length=200, verbose_name='Name', )
    committee_type = models.CharField(max_length=20, choices=COMMITTEE_TYPE_CHOICES, verbose_name='Typ', )
    description = models.TextField(blank=True, verbose_name='Beschreibung', )
    is_active = models.BooleanField(default=True, verbose_name='Aktiv', )
    parent = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='subcommittees',
        verbose_name='Übergeordnetes Gremium',
    )

    class Meta:
        verbose_name = 'Gremium'
        verbose_name_plural = 'Gremien'
        ordering = ['committee_type', 'name', ]

    def __str__(self):
        return f'{self.name} ({self.get_committee_type_display()})'
