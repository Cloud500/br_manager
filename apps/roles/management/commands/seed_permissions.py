"""Management command to seed default permissions."""

from django.core.management.base import BaseCommand

from apps.roles.models import Permission


class Command(BaseCommand):
    """Create default permissions for all apps."""
    
    help = 'Erstellt Standard-Berechtigungen für alle Apps'
    
    # Define all permissions as list of tuples
    # (codename, name, description, category)
    PERMISSIONS = [
        # System permissions
        ('system.admin', 'Systemweiter Admin-Zugriff', 
         'Voller Zugriff auf alle System-Funktionen', 'system'),
        ('system.manage_users', 'Benutzer verwalten',
         'Benutzer erstellen, bearbeiten und löschen', 'system'),
        
        # Role permissions
        ('role.create', 'Rolle erstellen',
         'Neue Rollen anlegen', 'role'),
        ('role.edit', 'Rolle bearbeiten',
         'Existierende Rollen bearbeiten', 'role'),
        ('role.delete', 'Rolle löschen',
         'Rollen löschen (außer System-Rollen)', 'role'),
        ('role.assign_permissions', 'Berechtigungen zuweisen',
         'Berechtigungen zu Rollen hinzufügen oder entfernen', 'role'),
        ('role.view', 'Rollen einsehen',
         'Liste aller Rollen anzeigen', 'role'),
        ('role.assign_to_member', 'Rolle zuweisen',
         'Rollen an Gremiumsmitglieder zuweisen', 'role'),
    ]
    
    def handle(self, *args, **options):
        """Execute command."""
        created_count = 0
        updated_count = 0
        
        for codename, name, description, category in self.PERMISSIONS:
            permission, created = Permission.objects.get_or_create(
                codename=codename,
                defaults={
                    'name': name,
                    'description': description,
                    'category': category
                }
            )
            
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'+ Created permission: {codename}')
                )
            else:
                # Update existing permission
                if (permission.name != name or 
                    permission.description != description or 
                    permission.category != category):
                    permission.name = name
                    permission.description = description
                    permission.category = category
                    permission.save()
                    updated_count += 1
                    self.stdout.write(
                        self.style.WARNING(f'* Updated permission: {codename}')
                    )
        
        # Summary
        self.stdout.write(
            self.style.SUCCESS(
                f'\nPermissions seeded successfully!'
            )
        )
        self.stdout.write(
            f'  Created: {created_count}'
        )
        self.stdout.write(
            f'  Updated: {updated_count}'
        )
        self.stdout.write(
            f'  Total: {len(self.PERMISSIONS)}'
        )
