from django.db import migrations


def seed_moving_company(apps, schema_editor):
    Role = apps.get_model('authentication', 'Role')
    Role.objects.get_or_create(
        name='MovingCompany',
        defaults={'description': 'Moving company registered to offer relocation services'},
    )


def unseed_moving_company(apps, schema_editor):
    Role = apps.get_model('authentication', 'Role')
    Role.objects.filter(name='MovingCompany').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('authentication', '0008_add_moving_company_profile'),
    ]

    operations = [
        migrations.RunPython(seed_moving_company, reverse_code=unseed_moving_company),
    ]
