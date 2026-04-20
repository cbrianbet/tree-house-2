from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('disputes', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='dispute',
            name='dispute_type',
            field=models.CharField(
                choices=[
                    ('rent', 'Rent'),
                    ('maintenance', 'Maintenance'),
                    ('noise', 'Noise'),
                    ('lease_terms', 'Lease Terms'),
                    ('deposit', 'Deposit'),
                    ('damage', 'Damage'),
                    ('other', 'Other'),
                ],
                max_length=20,
            ),
        ),
    ]
