from django.db import migrations


def seed_alert_rules(apps, schema_editor):
    AlertRule = apps.get_model('monitoring', 'AlertRule')

    rules = [
        {
            'name': 'High overdue invoice count (warning)',
            'metric_type': 'overdue_invoice_count',
            'condition': 'gte',
            'threshold_value': '10',
            'severity': 'warning',
            'description': 'More than 10 invoices are overdue across the platform.',
            'enabled': True,
        },
        {
            'name': 'Critical overdue invoice count',
            'metric_type': 'overdue_invoice_count',
            'condition': 'gte',
            'threshold_value': '50',
            'severity': 'critical',
            'description': 'More than 50 invoices are overdue — urgent action required.',
            'enabled': True,
        },
        {
            'name': 'Low platform occupancy rate',
            'metric_type': 'occupancy_rate',
            'condition': 'lte',
            'threshold_value': '70',
            'severity': 'warning',
            'description': 'Platform-wide occupancy rate has fallen to or below 70%.',
            'enabled': True,
        },
        {
            'name': 'High open maintenance count',
            'metric_type': 'open_maintenance_count',
            'condition': 'gte',
            'threshold_value': '20',
            'severity': 'warning',
            'description': 'More than 20 maintenance requests are unresolved.',
            'enabled': True,
        },
        {
            'name': 'High open dispute count',
            'metric_type': 'open_dispute_count',
            'condition': 'gte',
            'threshold_value': '5',
            'severity': 'warning',
            'description': 'More than 5 disputes are open or under review.',
            'enabled': True,
        },
        {
            'name': 'Low payment success rate',
            'metric_type': 'payment_success_rate',
            'condition': 'lte',
            'threshold_value': '80',
            'severity': 'critical',
            'description': 'Payment success rate has dropped below 80% in the last 30 days.',
            'enabled': True,
        },
    ]

    for rule_data in rules:
        AlertRule.objects.get_or_create(name=rule_data['name'], defaults=rule_data)


def reverse_seed(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('monitoring', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed_alert_rules, reverse_code=reverse_seed),
    ]
