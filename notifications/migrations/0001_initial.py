from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Notification',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('notification_type', models.CharField(
                    max_length=20,
                    choices=[
                        ('message', 'New Message'),
                        ('maintenance', 'Maintenance Update'),
                        ('payment', 'Payment'),
                        ('lease', 'Lease'),
                        ('dispute', 'Dispute'),
                        ('application', 'Application'),
                    ],
                )),
                ('title', models.CharField(max_length=200)),
                ('body', models.TextField()),
                ('action_url', models.CharField(max_length=500, blank=True)),
                ('is_read', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='notifications',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
    ]
