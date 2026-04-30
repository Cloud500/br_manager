from django.db import migrations, models


def populate_resolution_titles(apps, schema_editor):
    """Fill titles for existing resolutions from their proposal text."""
    Resolution = apps.get_model('resolutions', 'Resolution')
    for resolution in Resolution.objects.filter(title='').iterator():
        proposal = (resolution.proposal or '').strip()
        resolution.title = proposal[:255] or 'Beschluss'
        resolution.save(update_fields=['title'])


def clear_resolution_titles(apps, schema_editor):
    """Reverse data migration by clearing generated titles."""
    Resolution = apps.get_model('resolutions', 'Resolution')
    Resolution.objects.update(title='')


class Migration(migrations.Migration):

    dependencies = [
        ('resolutions', '9999_seed_resolution_permissions'),
    ]

    operations = [
        migrations.AddField(
            model_name='resolution',
            name='title',
            field=models.CharField(
                blank=True,
                default='',
                help_text='Kurzer Name zur übersichtlichen Anzeige des Beschlusses',
                max_length=255,
                verbose_name='Titel',
            ),
        ),
        migrations.RunPython(populate_resolution_titles, clear_resolution_titles),
        migrations.AlterField(
            model_name='resolution',
            name='title',
            field=models.CharField(
                help_text='Kurzer Name zur übersichtlichen Anzeige des Beschlusses',
                max_length=255,
                verbose_name='Titel',
            ),
        ),
    ]
