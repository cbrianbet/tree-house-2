from django.db import migrations, models


def forwards_priority_emergency_to_urgent(apps, schema_editor):
    MaintenanceRequest = apps.get_model('maintenance', 'MaintenanceRequest')
    MaintenanceRequest.objects.filter(priority='emergency').update(priority='urgent')


class Migration(migrations.Migration):

    dependencies = [
        ('maintenance', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(
            forwards_priority_emergency_to_urgent,
            migrations.RunPython.noop,
        ),
        migrations.AlterField(
            model_name='maintenancerequest',
            name='category',
            field=models.CharField(
                choices=[
                    ('plumbing', 'Plumbing'),
                    ('electrical', 'Electrical'),
                    ('structural', 'Structural'),
                    ('appliance', 'Appliance'),
                    ('capentry', 'Carpentry'),
                    ('painting', 'Painting'),
                    ('masonry', 'Masonry'),
                    ('other', 'Other'),
                ],
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name='maintenancerequest',
            name='priority',
            field=models.CharField(
                choices=[
                    ('low', 'Low'),
                    ('medium', 'Medium'),
                    ('high', 'High'),
                    ('urgent', 'Urgent'),
                ],
                default='medium',
                max_length=20,
            ),
        ),
    ]
