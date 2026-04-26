"""Management command to create committee permissions."""

from django.core.management.base import BaseCommand

from apps.roles.models import Permission


class Command(BaseCommand):
    """Create standard permissions for committees."""
    
    help = 'Erstellt Standard-Berechtigungen für Committees'
    
    def handle(self, *args, **options):
        """Execute command."""
        permissions = [
            ('committee.create', 'Gremium erstellen', 'committee'),
            ('committee.edit', 'Gremium bearbeiten', 'committee'),
            ('committee.view', 'Gremiumsdetails einsehen', 'committee'),
            ('committee.delete', 'Gremium löschen (soft-delete)', 'committee'),
            ('committee.manage_members', 'Mitglieder hinzufügen/entfernen/bearbeiten', 'committee'),
            ('committee.view_members', 'Mitgliederliste einsehen', 'committee'),
        ]
        
        created_count = 0
        for codename, description, category in permissions:
            permission, created = Permission.objects.get_or_create(
                codename=codename,
                defaults={
                    'name': description,
                    'category': category,
                }
            )
            
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'+ Created permission: {codename}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'- Permission already exists: {codename}')
                )
        
        self.stdout.write(
            self.style.SUCCESS(f'\nCreated {created_count} new permissions')
        )
