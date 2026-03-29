from django.db import migrations


def seed_artisan(apps, schema_editor):
    Role = apps.get_model('authentication', 'Role')
    Role.objects.get_or_create(name='Artisan', defaults={'description': 'Skilled tradesperson who bids on maintenance requests'})


def unseed_artisan(apps, schema_editor):
    Role = apps.get_model('authentication', 'Role')
    Role.objects.filter(name='Artisan').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('authentication', '0005_add_artisan_profile'),
    ]

    operations = [
        migrations.RunPython(seed_artisan, reverse_code=unseed_artisan),
    ]
