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
            all_perms = Permission.objects.all()
            
            assigned_count = 0
            for perm in all_perms:
                role_perm, created = RolePermission.objects.get_or_create(
                    role=system_admin,
                    permission=perm
                )
                if created:
                    assigned_count += 1
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'+ Assigned {assigned_count} permissions to SYSTEM_ADMIN'
                )
            )
        except Role.DoesNotExist:
            self.stdout.write(
                self.style.ERROR('! SYSTEM_ADMIN role not found')
            )
        
        # Assign committee permissions to committee roles
        self.stdout.write('\nAssigning permissions to committee roles...')
        
        committee_perms = Permission.objects.filter(category='committee')
        
        # CHAIR gets all committee permissions
        try:
            chair = Role.objects.get(codename='CHAIR')
            assigned_count = 0
            for perm in committee_perms:
                role_perm, created = RolePermission.objects.get_or_create(
                    role=chair,
                    permission=perm
                )
                if created:
                    assigned_count += 1
            self.stdout.write(
                self.style.SUCCESS(
                    f'+ Assigned {assigned_count} permissions to CHAIR'
                )
            )
        except Role.DoesNotExist:
            self.stdout.write(
                self.style.ERROR('! CHAIR role not found')
            )
        
        # VICE_CHAIR gets same as CHAIR
        try:
            vice_chair = Role.objects.get(codename='VICE_CHAIR')
            assigned_count = 0
            for perm in committee_perms:
                role_perm, created = RolePermission.objects.get_or_create(
                    role=vice_chair,
                    permission=perm
                )
                if created:
                    assigned_count += 1
            self.stdout.write(
                self.style.SUCCESS(
                    f'+ Assigned {assigned_count} permissions to VICE_CHAIR'
                )
            )
        except Role.DoesNotExist:
            self.stdout.write(
                self.style.ERROR('! VICE_CHAIR role not found')
            )
        
        # CLERK gets view and view_members permissions
        try:
            clerk = Role.objects.get(codename='CLERK')
            view_perms = committee_perms.filter(
                codename__in=['committee.view', 'committee.view_members']
            )
            assigned_count = 0
            for perm in view_perms:
                role_perm, created = RolePermission.objects.get_or_create(
                    role=clerk,
                    permission=perm
                )
                if created:
                    assigned_count += 1
            self.stdout.write(
                self.style.SUCCESS(
                    f'+ Assigned {assigned_count} permissions to CLERK'
                )
            )
        except Role.DoesNotExist:
            self.stdout.write(
                self.style.ERROR('! CLERK role not found')
            )
        
        # MEMBER gets view and view_members permissions
        try:
            member = Role.objects.get(codename='MEMBER')
            view_perms = committee_perms.filter(
                codename__in=['committee.view', 'committee.view_members']
            )
            assigned_count = 0
            for perm in view_perms:
                role_perm, created = RolePermission.objects.get_or_create(
                    role=member,
                    permission=perm
                )
                if created:
                    assigned_count += 1
            self.stdout.write(
                self.style.SUCCESS(
                    f'+ Assigned {assigned_count} permissions to MEMBER'
                )
            )
        except Role.DoesNotExist:
            self.stdout.write(
                self.style.ERROR('! MEMBER role not found')
            )
        
        # SUBSTITUTE gets view and view_members permissions
        try:
            substitute = Role.objects.get(codename='SUBSTITUTE')
            view_perms = committee_perms.filter(
                codename__in=['committee.view', 'committee.view_members']
            )
            assigned_count = 0
            for perm in view_perms:
                role_perm, created = RolePermission.objects.get_or_create(
                    role=substitute,
                    permission=perm
                )
                if created:
                    assigned_count += 1
            self.stdout.write(
                self.style.SUCCESS(
                    f'+ Assigned {assigned_count} permissions to SUBSTITUTE'
                )
            )
        except Role.DoesNotExist:
            self.stdout.write(
                self.style.ERROR('! SUBSTITUTE role not found')
            )
        
        # EXTERNAL_MEMBER and GUEST get only view permission
        for role_codename in ['EXTERNAL_MEMBER', 'GUEST']:
            try:
                role = Role.objects.get(codename=role_codename)
                view_perm = committee_perms.filter(codename='committee.view')
                assigned_count = 0
                for perm in view_perm:
                    role_perm, created = RolePermission.objects.get_or_create(
                        role=role,
                        permission=perm
                    )
                    if created:
                        assigned_count += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f'+ Assigned {assigned_count} permissions to {role_codename}'
                    )
                )
            except Role.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'! {role_codename} role not found')
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
