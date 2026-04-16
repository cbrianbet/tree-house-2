from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0003_billing_expansion'),
    ]

    operations = [
        migrations.AddField(
            model_name='payment',
            name='payment_method',
            field=models.CharField(
                choices=[
                    ('mpesa', 'M-Pesa'),
                    ('bank', 'Bank'),
                    ('card', 'Card'),
                    ('cash', 'Cash'),
                    ('other', 'Other'),
                ],
                default='other',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='payment',
            name='transaction_reference',
            field=models.CharField(blank=True, db_index=True, max_length=128, null=True),
        ),
        migrations.AddField(
            model_name='invoice',
            name='invoice_number',
            field=models.CharField(blank=True, db_index=True, default='', max_length=32),
            preserve_default=False,
        ),
    ]
