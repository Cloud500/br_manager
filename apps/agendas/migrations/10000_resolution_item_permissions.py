from django.db import migrations


def seed_resolution_item_permissions(apps, schema_editor):
    """Create and assign resolution TOP edit/delete permissions."""
    Permission = apps.get_model('roles', 'Permission')
    Role = apps.get_model('roles', 'Role')
    RolePermission = apps.get_model('roles', 'RolePermission')

    permissions_data = [
        (
            'agenda.edit_item_resolution',
            'Beschluss-TOP bearbeiten',
            'Beschluss-TOPs bearbeiten',
            'agenda',
        ),
        (
            'agenda.delete_item_resolution',
            'Beschluss-TOP löschen',
            'Beschluss-TOPs löschen',
            'agenda',
        ),
    ]

    created_permissions = {}
    for codename, name, description, category in permissions_data:
        permission, _created = Permission.objects.get_or_create(
            codename=codename,
            defaults={
                'name': name,
                'description': description,
                'category': category,
            },
        )
        created_permissions[codename] = permission

    role_codes = ['SYSTEM_ADMIN', 'CHAIR', 'VICE_CHAIR', 'CLERK']
    for role in Role.objects.filter(codename__in=role_codes):
        for permission in created_permissions.values():
            RolePermission.objects.get_or_create(role=role, permission=permission)


def reverse_resolution_item_permissions(apps, schema_editor):
    """Remove resolution TOP edit/delete permissions."""
    Permission = apps.get_model('roles', 'Permission')
    RolePermission = apps.get_model('roles', 'RolePermission')
    permissions = Permission.objects.filter(
        codename__in=['agenda.edit_item_resolution', 'agenda.delete_item_resolution']
    )
    RolePermission.objects.filter(permission__in=permissions).delete()
    permissions.delete()


class Migration(migrations.Migration):

    dependencies = [
        ('agendas', '9999_seed_agenda_permissions'),
        ('roles', '9999_seed_roles_and_permissions'),
    ]

    operations = [
        migrations.RunPython(seed_resolution_item_permissions, reverse_resolution_item_permissions),
    ]
