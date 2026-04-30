# Generated migration for agenda permissions

from django.db import migrations


def seed_agenda_permissions(apps, schema_editor):
    """Create and assign agenda permissions."""
    Permission = apps.get_model('roles', 'Permission')
    Role = apps.get_model('roles', 'Role')
    RolePermission = apps.get_model('roles', 'RolePermission')
    
    # Define all permissions
    permissions_data = [
        # Agenda base permission
        ('agenda.view', 'Tagesordnung ansehen',
         'Tagesordnungen ansehen', 'agenda'),
        
        # Regular item permissions
        ('agenda.add_item_regular', 'Normalen TOP hinzufügen',
         'Normale TOPs erstellen', 'agenda'),
        ('agenda.edit_item_regular', 'Normalen TOP bearbeiten',
         'Normale TOPs bearbeiten', 'agenda'),
        ('agenda.delete_item_regular', 'Normalen TOP löschen',
         'Normale TOPs löschen', 'agenda'),
        ('agenda.add_item_resolution', 'Beschluss-TOP hinzufügen',
         'Beschlüsse zur Tagesordnung hinzufügen', 'agenda'),
        ('agenda.reorder_items', 'TOPs neu anordnen',
         'Reihenfolge und Hierarchie ändern', 'agenda'),
    ]
    
    # Create permissions
    created_permissions = {}
    for codename, name, description, category in permissions_data:
        permission, created = Permission.objects.get_or_create(
            codename=codename,
            defaults={
                'name': name,
                'description': description,
                'category': category
            }
        )
        created_permissions[codename] = permission
    
    # Assign all agenda permissions to SYSTEM_ADMIN
    try:
        system_admin = Role.objects.get(codename='SYSTEM_ADMIN')
        for permission in created_permissions.values():
            RolePermission.objects.get_or_create(
                role=system_admin,
                permission=permission
            )
    except Role.DoesNotExist:
        pass
    
    # CHAIR gets: all 5 permissions
    try:
        chair = Role.objects.get(codename='CHAIR')
        chair_perm_codes = [
            'agenda.view', 'agenda.add_item_regular', 'agenda.edit_item_regular',
            'agenda.delete_item_regular', 'agenda.add_item_resolution', 'agenda.reorder_items'
        ]
        for code in chair_perm_codes:
            perm = created_permissions.get(code)
            if perm:
                RolePermission.objects.get_or_create(
                    role=chair,
                    permission=perm
                )
    except Role.DoesNotExist:
        pass
    
    # VICE_CHAIR gets: all 5 permissions
    try:
        vice_chair = Role.objects.get(codename='VICE_CHAIR')
        vice_chair_perm_codes = [
            'agenda.view', 'agenda.add_item_regular', 'agenda.edit_item_regular',
            'agenda.delete_item_regular', 'agenda.add_item_resolution', 'agenda.reorder_items'
        ]
        for code in vice_chair_perm_codes:
            perm = created_permissions.get(code)
            if perm:
                RolePermission.objects.get_or_create(
                    role=vice_chair,
                    permission=perm
                )
    except Role.DoesNotExist:
        pass
    
    # CLERK gets: all 5 permissions
    try:
        clerk = Role.objects.get(codename='CLERK')
        clerk_perm_codes = [
            'agenda.view', 'agenda.add_item_regular', 'agenda.edit_item_regular',
            'agenda.delete_item_regular', 'agenda.add_item_resolution', 'agenda.reorder_items'
        ]
        for code in clerk_perm_codes:
            perm = created_permissions.get(code)
            if perm:
                RolePermission.objects.get_or_create(
                    role=clerk,
                    permission=perm
                )
    except Role.DoesNotExist:
        pass
    
    # MEMBER gets: only agenda.view
    # Note: BA members get extended permissions via committee-type check in views
    try:
        member = Role.objects.get(codename='MEMBER')
        member_perm_codes = ['agenda.view']
        for code in member_perm_codes:
            perm = created_permissions.get(code)
            if perm:
                RolePermission.objects.get_or_create(
                    role=member,
                    permission=perm
                )
    except Role.DoesNotExist:
        pass
    
    # SUBSTITUTE gets: no permissions
    # EXTERNAL_MEMBER gets: no permissions
    # GUEST gets: no permissions


def reverse_seed_permissions(apps, schema_editor):
    """Remove agenda permissions."""
    Permission = apps.get_model('roles', 'Permission')
    RolePermission = apps.get_model('roles', 'RolePermission')
    
    # Delete all RolePermissions for agenda permissions
    agenda_permissions = Permission.objects.filter(category='agenda')
    RolePermission.objects.filter(permission__in=agenda_permissions).delete()
    
    # Delete all agenda permissions
    agenda_permissions.delete()


class Migration(migrations.Migration):

    dependencies = [
        ("agendas", "0001_initial"),
        ("roles", "9999_seed_roles_and_permissions"),  # Ensure roles exist first
    ]

    operations = [
        migrations.RunPython(seed_agenda_permissions, reverse_seed_permissions),
    ]
