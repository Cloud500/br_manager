"""Management command to seed default roles."""

from django.core.management.base import BaseCommand

from apps.roles.models import Permission, Role, RolePermission


class Command(BaseCommand):
    """Create default roles (system + committee)."""
    
    help = 'Erstellt Standard-Rollen (System + Gremien)'
    
    # Define system roles (codename, name, description, role_type, sort_order)
    SYSTEM_ROLES = [
        ('SYSTEM_ADMIN', 'System-Administrator', 
         'Vollständige System-Administration', 'SYSTEM', 1),
        ('USER', 'Benutzer', 
         'Standard-Benutzer ohne besondere Rechte', 'SYSTEM', 100),
    ]
    
    # Define committee roles (codename, name, description, role_type, sort_order)
    COMMITTEE_ROLES = [
        ('CHAIR', 'Vorsitz',
         'Vorsitzender des Gremiums', 'COMMITTEE', 1),
        ('VICE_CHAIR', 'Stellv. Vorsitz',
         'Stellvertretender Vorsitzender', 'COMMITTEE', 2),
        ('CLERK', 'Schriftführung',
         'Schriftführer des Gremiums', 'COMMITTEE', 3),
        ('MEMBER', 'Mitglied',
         'Reguläres Gremiumsmitglied', 'COMMITTEE', 10),
        ('SUBSTITUTE', 'Ersatzmitglied',
         'Ersatzmitglied für reguläre Mitglieder', 'COMMITTEE', 20),
        ('EXTERNAL_MEMBER', 'Externes Mitglied',
         'Externes Mitglied ohne Stimmrecht', 'COMMITTEE', 30),
        ('GUEST', 'Gast',
         'Gast ohne Stimmrecht', 'COMMITTEE', 40),
    ]
    
    def handle(self, *args, **options):
        """Execute command."""
        created_count = 0
        updated_count = 0
        
        # Create system roles
        self.stdout.write('\nCreating system roles...')
        for codename, name, description, role_type, sort_order in self.SYSTEM_ROLES:
            role, created = Role.objects.get_or_create(
                codename=codename,
                defaults={
                    'name': name,
                    'description': description,
                    'role_type': role_type,
                    'is_system_role': True,
                    'sort_order': sort_order
                }
            )
            
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'+ Created system role: {codename}')
                )
            else:
                # Update existing role
                if (role.name != name or role.description != description 
                    or role.sort_order != sort_order):
                    role.name = name
                    role.description = description
                    role.sort_order = sort_order
                    role.save()
                    updated_count += 1
                    self.stdout.write(
                        self.style.WARNING(f'* Updated system role: {codename}')
                    )
        
        # Create committee roles
        self.stdout.write('\nCreating committee roles...')
        for codename, name, description, role_type, sort_order in self.COMMITTEE_ROLES:
            role, created = Role.objects.get_or_create(
                codename=codename,
                defaults={
                    'name': name,
                    'description': description,
                    'role_type': role_type,
                    'is_system_role': True,
                    'sort_order': sort_order
                }
            )
            
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'+ Created committee role: {codename}')
                )
            else:
                if (role.name != name or role.description != description 
                    or role.sort_order != sort_order):
                    role.name = name
                    role.description = description
                    role.sort_order = sort_order
                    role.save()
                    updated_count += 1
                    self.stdout.write(
                        self.style.WARNING(f'* Updated committee role: {codename}')
                    )
        
        # Assign all system permissions to SYSTEM_ADMIN
        self.stdout.write('\nAssigning permissions to SYSTEM_ADMIN...')
        try:
            system_admin = Role.objects.get(codename='SYSTEM_ADMIN')
            system_perms = Permission.objects.filter(category='system')
            
            assigned_count = 0
            for perm in system_perms:
                role_perm, created = RolePermission.objects.get_or_create(
                    role=system_admin,
                    permission=perm
                )
                if created:
                    assigned_count += 1
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'+ Assigned {assigned_count} system permissions to SYSTEM_ADMIN'
                )
            )
        except Role.DoesNotExist:
            self.stdout.write(
                self.style.ERROR('! SYSTEM_ADMIN role not found')
            )
        
        # Summary
        total_roles = len(self.SYSTEM_ROLES) + len(self.COMMITTEE_ROLES)
        self.stdout.write(
            self.style.SUCCESS(
                f'\nRoles seeded successfully!'
            )
        )
        self.stdout.write(
            f'  Created: {created_count}'
        )
        self.stdout.write(
            f'  Updated: {updated_count}'
        )
        self.stdout.write(
            f'  Total: {total_roles}'
        )
