from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('authentication', '0004_seed_roles'),
    ]

    operations = [
        migrations.CreateModel(
            name='ArtisanProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('trade', models.CharField(choices=[('plumbing', 'Plumbing'), ('electrical', 'Electrical'), ('carpentry', 'Carpentry'), ('painting', 'Painting'), ('masonry', 'Masonry'), ('other', 'Other')], max_length=50)),
                ('bio', models.TextField(blank=True)),
                ('rating', models.DecimalField(decimal_places=2, default=0, max_digits=3)),
                ('verified', models.BooleanField(default=False)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='artisan_profile', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
