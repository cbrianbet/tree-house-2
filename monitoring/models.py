from django.db import models
from django.conf import settings


METRIC_TYPES = [
    ('overdue_invoice_count', 'Overdue Invoice Count'),
    ('monthly_revenue', 'Monthly Revenue'),
    ('occupancy_rate', 'Occupancy Rate (%)'),
    ('open_maintenance_count', 'Open Maintenance Count'),
    ('open_dispute_count', 'Open Dispute Count'),
    ('pending_application_count', 'Pending Application Count'),
    ('payment_success_rate', 'Payment Success Rate (%)'),
]


class SystemMetric(models.Model):
    metric_type = models.CharField(max_length=50, choices=METRIC_TYPES)
    value = models.DecimalField(max_digits=15, decimal_places=2)
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-recorded_at']
        indexes = [
            models.Index(fields=['metric_type', 'recorded_at'], name='monitoring_metric_type_idx'),
        ]

    def __str__(self):
        return f"{self.metric_type}: {self.value} @ {self.recorded_at}"


class AlertRule(models.Model):
    CONDITIONS = [
        ('gt', 'Greater than'),
        ('gte', 'Greater than or equal'),
        ('lt', 'Less than'),
        ('lte', 'Less than or equal'),
    ]
    SEVERITIES = [
        ('info', 'Info'),
        ('warning', 'Warning'),
        ('critical', 'Critical'),
    ]

    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    metric_type = models.CharField(max_length=50, choices=METRIC_TYPES)
    condition = models.CharField(max_length=3, choices=CONDITIONS)
    threshold_value = models.DecimalField(max_digits=15, decimal_places=2)
    severity = models.CharField(max_length=10, choices=SEVERITIES, default='warning')
    enabled = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='alert_rules',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.severity})"


class AlertInstance(models.Model):
    STATUSES = [
        ('triggered', 'Triggered'),
        ('acknowledged', 'Acknowledged'),
        ('resolved', 'Resolved'),
    ]

    rule = models.ForeignKey(AlertRule, on_delete=models.CASCADE, related_name='instances')
    status = models.CharField(max_length=15, choices=STATUSES, default='triggered')
    triggered_at = models.DateTimeField(auto_now_add=True)
    triggered_value = models.DecimalField(max_digits=15, decimal_places=2)
    acknowledged_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='acknowledged_alerts',
    )
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    note = models.TextField(blank=True)

    class Meta:
        ordering = ['-triggered_at']

    def __str__(self):
        return f"Alert: {self.rule.name} @ {self.triggered_at} ({self.status})"
