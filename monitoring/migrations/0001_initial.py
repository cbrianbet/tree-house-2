from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='SystemMetric',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('metric_type', models.CharField(
                    max_length=50,
                    choices=[
                        ('overdue_invoice_count', 'Overdue Invoice Count'),
                        ('monthly_revenue', 'Monthly Revenue'),
                        ('occupancy_rate', 'Occupancy Rate (%)'),
                        ('open_maintenance_count', 'Open Maintenance Count'),
                        ('open_dispute_count', 'Open Dispute Count'),
                        ('pending_application_count', 'Pending Application Count'),
                        ('payment_success_rate', 'Payment Success Rate (%)'),
                    ],
                )),
                ('value', models.DecimalField(max_digits=15, decimal_places=2)),
                ('recorded_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'ordering': ['-recorded_at'],
            },
        ),
        migrations.AddIndex(
            model_name='systemmetric',
            index=models.Index(fields=['metric_type', 'recorded_at'], name='monitoring_metric_type_idx'),
        ),
        migrations.CreateModel(
            name='AlertRule',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('description', models.TextField(blank=True)),
                ('metric_type', models.CharField(
                    max_length=50,
                    choices=[
                        ('overdue_invoice_count', 'Overdue Invoice Count'),
                        ('monthly_revenue', 'Monthly Revenue'),
                        ('occupancy_rate', 'Occupancy Rate (%)'),
                        ('open_maintenance_count', 'Open Maintenance Count'),
                        ('open_dispute_count', 'Open Dispute Count'),
                        ('pending_application_count', 'Pending Application Count'),
                        ('payment_success_rate', 'Payment Success Rate (%)'),
                    ],
                )),
                ('condition', models.CharField(
                    max_length=3,
                    choices=[
                        ('gt', 'Greater than'),
                        ('gte', 'Greater than or equal'),
                        ('lt', 'Less than'),
                        ('lte', 'Less than or equal'),
                    ],
                )),
                ('threshold_value', models.DecimalField(max_digits=15, decimal_places=2)),
                ('severity', models.CharField(
                    max_length=10,
                    choices=[
                        ('info', 'Info'),
                        ('warning', 'Warning'),
                        ('critical', 'Critical'),
                    ],
                    default='warning',
                )),
                ('enabled', models.BooleanField(default=True)),
                ('created_by', models.ForeignKey(
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='alert_rules',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name='AlertInstance',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('rule', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='instances',
                    to='monitoring.alertrule',
                )),
                ('status', models.CharField(
                    max_length=15,
                    choices=[
                        ('triggered', 'Triggered'),
                        ('acknowledged', 'Acknowledged'),
                        ('resolved', 'Resolved'),
                    ],
                    default='triggered',
                )),
                ('triggered_at', models.DateTimeField(auto_now_add=True)),
                ('triggered_value', models.DecimalField(max_digits=15, decimal_places=2)),
                ('acknowledged_by', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='acknowledged_alerts',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('acknowledged_at', models.DateTimeField(blank=True, null=True)),
                ('resolved_at', models.DateTimeField(blank=True, null=True)),
                ('note', models.TextField(blank=True)),
            ],
            options={
                'ordering': ['-triggered_at'],
            },
        ),
    ]
