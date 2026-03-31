from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('authentication', '0009_seed_moving_company_role'),
    ]

    operations = [
        migrations.CreateModel(
            name='RoleChangeLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('reason', models.TextField(blank=True)),
                ('changed_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='role_change_logs', to=settings.AUTH_USER_MODEL)),
                ('changed_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='role_changes_made', to=settings.AUTH_USER_MODEL)),
                ('old_role', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='authentication.role')),
                ('new_role', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='authentication.role')),
            ],
        ),
    ]
