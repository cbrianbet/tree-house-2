from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('authentication', '0009_seed_moving_company_role'),
        ('property', '0008_add_search_features'),
    ]

    operations = [
        migrations.CreateModel(
            name='NeighborhoodInsight',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('insight_type', models.CharField(
                    choices=[
                        ('school', 'School'),
                        ('hospital', 'Hospital'),
                        ('safety', 'Safety'),
                        ('transit', 'Transit'),
                        ('restaurant', 'Restaurant'),
                        ('other', 'Other'),
                    ],
                    max_length=20,
                )),
                ('name', models.CharField(max_length=255)),
                ('address', models.CharField(blank=True, max_length=255)),
                ('distance_km', models.DecimalField(blank=True, decimal_places=2, max_digits=6, null=True)),
                ('rating', models.DecimalField(blank=True, decimal_places=1, max_digits=3, null=True)),
                ('lat', models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True)),
                ('lng', models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True)),
                ('notes', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('property', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='neighborhood_insights', to='property.property')),
                ('added_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='added_insights', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
