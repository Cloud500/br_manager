"""Custom managers for agendas app."""

from typing import Any
from uuid import UUID

from django.db import models


class AgendaQuerySet(models.QuerySet):
    """Custom QuerySet for Agenda model."""
    
    def finalized(self) -> 'AgendaQuerySet':
        """
        Filter agendas that are finalized.
        
        Returns only agendas where the meeting status is 'SENT'.
        
        Returns:
            QuerySet of finalized agendas
        """
        return self.filter(meeting__status='SENT')
    
    def editable(self) -> 'AgendaQuerySet':
        """
        Filter agendas that are still editable.
        
        Returns only agendas where the meeting status is 'DRAFT' or 'IN_PROGRESS'.
        
        Returns:
            QuerySet of editable agendas
        """
        return self.filter(meeting__status__in=['DRAFT', 'IN_PROGRESS'])
    
    def for_committee(self, committee_id: UUID) -> 'AgendaQuerySet':
        """
        Filter agendas for a specific committee.
        
        Args:
            committee_id: UUID of the committee
        
        Returns:
            QuerySet of agendas for the specified committee
        """
        return self.filter(meeting__committee_id=committee_id)


class AgendaManager(models.Manager):
    """Custom manager for Agenda model."""
    
    def get_queryset(self) -> AgendaQuerySet:
        """Return custom QuerySet."""
        return AgendaQuerySet(self.model, using=self._db)
    
    def finalized(self) -> AgendaQuerySet:
        """Return only finalized agendas."""
        return self.get_queryset().finalized()
    
    def editable(self) -> AgendaQuerySet:
        """Return only editable agendas."""
        return self.get_queryset().editable()
    
    def for_committee(self, committee_id: UUID) -> AgendaQuerySet:
        """Return agendas for specific committee."""
        return self.get_queryset().for_committee(committee_id)
