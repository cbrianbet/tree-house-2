from django.db import migrations, models


def backfill_payments(apps, schema_editor):
    Payment = apps.get_model('billing', 'Payment')
    for payment in Payment.objects.all().iterator():
        changed = False

        if not payment.transaction_reference and payment.stripe_charge_id:
            payment.transaction_reference = payment.stripe_charge_id
            changed = True

        if payment.payment_method == 'other':
            if payment.stripe_payment_intent_id and not payment.stripe_payment_intent_id.startswith('manual-'):
                payment.payment_method = 'card'
                changed = True
            elif payment.stripe_charge_id:
                payment.payment_method = 'card'
                changed = True

        if changed:
            payment.save(update_fields=['payment_method', 'transaction_reference'])


def backfill_invoice_numbers(apps, schema_editor):
    Invoice = apps.get_model('billing', 'Invoice')
    for invoice in Invoice.objects.filter(invoice_number='').order_by('pk').iterator():
        invoice.invoice_number = f'INV-{invoice.pk:04d}'
        invoice.save(update_fields=['invoice_number'])


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0004_add_payment_method_transaction_ref_invoice_number'),
    ]

    operations = [
        migrations.RunPython(backfill_payments, noop),
        migrations.RunPython(backfill_invoice_numbers, noop),
        migrations.AlterField(
            model_name='invoice',
            name='invoice_number',
            field=models.CharField(blank=True, db_index=True, max_length=32, unique=True),
        ),
    ]
