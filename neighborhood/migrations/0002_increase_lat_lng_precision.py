from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('neighborhood', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='neighborhoodinsight',
            name='lat',
            field=models.DecimalField(blank=True, decimal_places=10, max_digits=15, null=True),
        ),
        migrations.AlterField(
            model_name='neighborhoodinsight',
            name='lng',
            field=models.DecimalField(blank=True, decimal_places=10, max_digits=15, null=True),
        ),
    ]
