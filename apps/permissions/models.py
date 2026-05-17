from django.db import models
from config.models import BaseModel


class Permission(BaseModel):
    key = models.CharField(max_length=255, unique=True, verbose_name='Schlüssel', )
    description = models.TextField(blank=True, verbose_name='Beschreibung',)
    category = models.CharField(max_length=255, verbose_name='Kategorie',)

    def __str__(self):
        return self.key


class Role(BaseModel):
    name = models.CharField(max_length=255, unique=True, verbose_name='Name',)
    description = models.TextField(blank=True, verbose_name='Beschreibung',)
    system = models.BooleanField(default=False, verbose_name='System-Rolle',)
    permissions = models.ManyToManyField(
        Permission,
        blank=True,
        related_name="roles",
        verbose_name='Berechtigung',
    )

    def __str__(self):
        return self.name
