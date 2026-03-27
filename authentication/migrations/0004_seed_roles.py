from django.db import migrations


ROLES = [
    ('Admin', 'Platform administrator with full access'),
    ('Landlord', 'Property owner who lists properties for rent'),
    ('Agent', 'Manages properties on behalf of landlords'),
    ('Tenant', 'Rents properties'),
]


def seed_roles(apps, schema_editor):
    Role = apps.get_model('authentication', 'Role')
    for name, description in ROLES:
        Role.objects.get_or_create(name=name, defaults={'description': description})


def unseed_roles(apps, schema_editor):
    Role = apps.get_model('authentication', 'Role')
    Role.objects.filter(name__in=[name for name, _ in ROLES]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('authentication', '0003_add_profile_models'),
    ]

    operations = [
        migrations.RunPython(seed_roles, reverse_code=unseed_roles),
    ]
