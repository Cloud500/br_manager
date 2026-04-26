"""Management command to assign committee permissions to SYSTEM_ADMIN role."""

from django.core.management.base import BaseCommand

from apps.roles.models import Permission, Role, RolePermission


class Command(BaseCommand):
    """Assign committee permissions to SYSTEM_ADMIN role."""
    
    help = 'Weist SYSTEM_ADMIN alle committee-Permissions zu'
    
    def handle(self, *args, **options):
        """Execute command."""
        try:
            system_admin = Role.objects.get(codename='SYSTEM_ADMIN')
        except Role.DoesNotExist:
            self.stdout.write(
                self.style.ERROR('SYSTEM_ADMIN role not found. Please run seed_roles first.')
            )
            return
        
        # Get all committee permissions
        permissions = Permission.objects.filter(category='committee')
        
        if not permissions.exists():
            self.stdout.write(
                self.style.ERROR('No committee permissions found. Please run seed_committee_permissions first.')
            )
            return
        
        assigned_count = 0
        for permission in permissions:
            _, created = RolePermission.objects.get_or_create(
                role=system_admin,
                permission=permission
            )
            
            if created:
                assigned_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Assigned: {permission.codename} to SYSTEM_ADMIN')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'- Already assigned: {permission.codename}')
                )
        
        self.stdout.write(
            self.style.SUCCESS(f'\nAssigned {assigned_count} new permissions to SYSTEM_ADMIN')
        )
