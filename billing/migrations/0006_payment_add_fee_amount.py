from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0005_backfill_payment_method_invoice_number'),
    ]

    operations = [
        migrations.AddField(
            model_name='payment',
            name='fee_amount',
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                help_text='Optional per-payment fee, not counted towards invoice principal.',
                max_digits=10,
            ),
            preserve_default=False,
        ),
    ]
