# Generated migration for agenda item resolution permissions

from django.db import migrations


def add_resolution_item_permission(apps, schema_editor):
    """Add permission for adding resolution items to agenda."""
    Permission = apps.get_model('roles', 'Permission')
    Role = apps.get_model('roles', 'Role')
    RolePermission = apps.get_model('roles', 'RolePermission')
    
    # Create permission
    permission, created = Permission.objects.get_or_create(
        codename='agenda.add_item_resolution',
        defaults={
            'name': 'Beschluss-TOP hinzufügen',
            'description': 'Beschlüsse zur Tagesordnung hinzufügen',
            'category': 'agenda'
        }
    )
    
    # Assign to roles that can add agenda items
    role_codenames = ['SYSTEM_ADMIN', 'CHAIR', 'VICE_CHAIR', 'CLERK']
    
    for role_codename in role_codenames:
        try:
            role = Role.objects.get(codename=role_codename)
            RolePermission.objects.get_or_create(
                role=role,
                permission=permission
            )
        except Role.DoesNotExist:
            pass


def remove_resolution_item_permission(apps, schema_editor):
    """Remove resolution item permission."""
    Permission = apps.get_model('roles', 'Permission')
    RolePermission = apps.get_model('roles', 'RolePermission')
    
    try:
        permission = Permission.objects.get(codename='agenda.add_item_resolution')
        RolePermission.objects.filter(permission=permission).delete()
        permission.delete()
    except Permission.DoesNotExist:
        pass


class Migration(migrations.Migration):

    dependencies = [
        ('agendas', '9999_seed_agenda_permissions'),
        ('agendas', '0003_agendaitemresolution'),
    ]

    operations = [
        migrations.RunPython(add_resolution_item_permission, remove_resolution_item_permission),
    ]
