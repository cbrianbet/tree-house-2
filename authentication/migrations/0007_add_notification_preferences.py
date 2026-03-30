from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('authentication', '0006_seed_artisan_role'),
    ]

    operations = [
        migrations.CreateModel(
            name='NotificationPreference',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('email_notifications', models.BooleanField(default=True)),
                ('payment_due_reminder', models.BooleanField(default=True)),
                ('payment_received', models.BooleanField(default=True)),
                ('maintenance_updates', models.BooleanField(default=True)),
                ('new_maintenance_request', models.BooleanField(default=True)),
                ('new_application', models.BooleanField(default=True)),
                ('application_status_change', models.BooleanField(default=True)),
                ('lease_expiry_notice', models.BooleanField(default=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='notification_preferences',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
        ),
    ]
