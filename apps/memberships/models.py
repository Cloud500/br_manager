from django.db import models
from config.models import BaseModel
from django.conf import settings

from apps.committees.models import Committee
from apps.permissions.models import Role


class Membership(BaseModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='memberships',
        verbose_name='Benutzer'
    )
    committee = models.ForeignKey(
        Committee,
        on_delete=models.CASCADE,
        related_name='memberships',
        verbose_name='Gremium'
    )
    role = models.ForeignKey(
        Role,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='memberships',
        verbose_name='Rolle'
    )

    class Meta:
        unique_together = ("user", "committee")

    def __str__(self):
        return f"{self.user}@{self.committee} ({self.role})"
