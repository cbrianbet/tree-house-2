from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('monitoring', '0002_seed_alert_rules'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ImpersonationLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('admin', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='impersonation_actions',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('target_user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='impersonated_by',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('path', models.CharField(max_length=255)),
                ('method', models.CharField(max_length=10)),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'ordering': ['-timestamp'],
            },
        ),
    ]
