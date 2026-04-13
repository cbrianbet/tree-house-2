from django.db import migrations


def mark_admin_role_users_staff(apps, schema_editor):
    CustomUser = apps.get_model('authentication', 'CustomUser')
    Role = apps.get_model('authentication', 'Role')

    admin_role = Role.objects.filter(name='Admin').first()
    if not admin_role:
        return

    CustomUser.objects.filter(role=admin_role).update(is_staff=True)


def noop_reverse(apps, schema_editor):
    # Keep staff flags untouched on rollback to avoid accidental privilege drops.
    return


class Migration(migrations.Migration):

    dependencies = [
        ('authentication', '0009_seed_moving_company_role'),
    ]

    operations = [
        migrations.RunPython(mark_admin_role_users_staff, reverse_code=noop_reverse),
    ]
