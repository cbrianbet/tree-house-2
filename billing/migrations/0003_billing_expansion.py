from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0002_add_expense_chargetype_additionalincome'),
        ('property', '0005_add_property_agent'),
    ]

    operations = [
        migrations.AddField(
            model_name='billingconfig',
            name='invoice_lead_days',
            field=models.PositiveSmallIntegerField(default=0, help_text='Days before rent_due_day to generate invoice (0 = on due day).'),
        ),
        migrations.AddField(
            model_name='billingconfig',
            name='late_fee_mode',
            field=models.CharField(
                choices=[('percentage', 'Percentage'), ('fixed', 'Fixed')],
                default='percentage',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='billingconfig',
            name='late_fee_fixed_amount',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True),
        ),
        migrations.AddField(
            model_name='billingconfig',
            name='mpesa_paybill',
            field=models.CharField(blank=True, max_length=50),
        ),
        migrations.AddField(
            model_name='billingconfig',
            name='mpesa_account_label',
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name='billingconfig',
            name='bank_name',
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.AddField(
            model_name='billingconfig',
            name='bank_account',
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name='billingconfig',
            name='payment_notes',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='chargetype',
            name='charge_kind',
            field=models.CharField(
                choices=[('fixed', 'Fixed'), ('variable', 'Variable'), ('per_unit', 'Per unit')],
                default='variable',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='chargetype',
            name='default_amount',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True),
        ),
        migrations.AddField(
            model_name='chargetype',
            name='description',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='chargetype',
            name='display_order',
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='chargetype',
            name='is_active',
            field=models.BooleanField(default=True),
        ),
        migrations.CreateModel(
            name='PropertyBillingNotificationSettings',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                (
                    'remind_before_due_days',
                    models.PositiveSmallIntegerField(
                        blank=True,
                        help_text='Days before due_date to send pre-due reminder; null disables. If no settings row exists, legacy default 3 applies.',
                        null=True,
                    ),
                ),
                (
                    'remind_after_overdue_days',
                    models.PositiveSmallIntegerField(
                        blank=True,
                        help_text='Days after due_date before sending overdue reminder; null/0 sends as soon as invoice is overdue.',
                        null=True,
                    ),
                ),
                ('send_receipt_on_payment', models.BooleanField(default=True)),
                (
                    'property',
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='billing_notification_settings',
                        to='property.property',
                    ),
                ),
            ],
            options={
                'verbose_name': 'Property billing notification settings',
                'verbose_name_plural': 'Property billing notification settings',
            },
        ),
    ]
