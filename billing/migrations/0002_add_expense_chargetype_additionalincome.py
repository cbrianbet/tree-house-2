from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0001_initial'),
        ('maintenance', '0001_initial'),
        ('property', '0005_add_property_agent'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ChargeType',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('property', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='charge_types', to='property.property')),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='created_charge_types', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'unique_together': {('property', 'name')},
            },
        ),
        migrations.CreateModel(
            name='AdditionalIncome',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('date', models.DateField()),
                ('description', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('unit', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='additional_income', to='property.unit')),
                ('charge_type', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='income_entries', to='billing.chargetype')),
                ('recorded_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='recorded_income', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Expense',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('category', models.CharField(choices=[('maintenance', 'Maintenance'), ('utility', 'Utility'), ('insurance', 'Insurance'), ('tax', 'Tax'), ('repair', 'Repair'), ('management_fee', 'Management Fee'), ('other', 'Other')], max_length=20)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('description', models.TextField(blank=True)),
                ('date', models.DateField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('property', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='expenses', to='property.property')),
                ('unit', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='expenses', to='property.unit')),
                ('maintenance_request', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='expenses', to='maintenance.maintenancerequest')),
                ('recorded_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='recorded_expenses', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
