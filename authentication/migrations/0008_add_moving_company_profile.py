from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('authentication', '0007_add_notification_preferences'),
    ]

    operations = [
        migrations.CreateModel(
            name='MovingCompanyProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('company_name', models.CharField(blank=True, max_length=100)),
                ('description', models.TextField(blank=True)),
                ('phone', models.CharField(blank=True, max_length=20)),
                ('address', models.CharField(blank=True, max_length=255)),
                ('city', models.CharField(blank=True, max_length=100)),
                ('service_areas', models.JSONField(blank=True, default=list)),
                ('base_price', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('price_per_km', models.DecimalField(decimal_places=2, default=0, max_digits=6)),
                ('is_verified', models.BooleanField(default=False)),
                ('is_active', models.BooleanField(default=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='moving_company_profile', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
