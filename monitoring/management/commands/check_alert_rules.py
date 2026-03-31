from django.core.management.base import BaseCommand
from django.utils import timezone


_CONDITION_FNS = {
    'gt': lambda val, threshold: val > threshold,
    'gte': lambda val, threshold: val >= threshold,
    'lt': lambda val, threshold: val < threshold,
    'lte': lambda val, threshold: val <= threshold,
}


class Command(BaseCommand):
    help = 'Evaluate enabled alert rules against latest metrics; fire or auto-resolve AlertInstances'

    def handle(self, *args, **options):
        from monitoring.models import AlertRule, AlertInstance, SystemMetric

        rules = AlertRule.objects.filter(enabled=True).select_related('created_by')
        fired = 0
        resolved = 0

        for rule in rules:
            metric = (
                SystemMetric.objects.filter(metric_type=rule.metric_type)
                .order_by('-recorded_at')
                .first()
            )
            if metric is None:
                self.stdout.write(f'  [SKIP] No metric data for {rule.metric_type}')
                continue

            condition_fn = _CONDITION_FNS.get(rule.condition)
            if condition_fn is None:
                continue

            breached = condition_fn(metric.value, rule.threshold_value)

            existing_open = AlertInstance.objects.filter(
                rule=rule, status__in=['triggered', 'acknowledged']
            ).first()

            if breached and not existing_open:
                alert = AlertInstance.objects.create(
                    rule=rule,
                    triggered_value=metric.value,
                )
                fired += 1
                self.stdout.write(
                    self.style.WARNING(
                        f'  [{rule.severity.upper()}] Fired: {rule.name} '
                        f'(value={metric.value}, threshold={rule.condition} {rule.threshold_value})'
                    )
                )
                self._notify_admins(rule, metric.value, alert)

            elif not breached and existing_open:
                existing_open.status = 'resolved'
                existing_open.resolved_at = timezone.now()
                existing_open.note = 'Auto-resolved: metric returned to normal range.'
                existing_open.save()
                resolved += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f'  [RESOLVED] {rule.name} (value={metric.value})'
                    )
                )

        self.stdout.write(
            self.style.SUCCESS(
                f'✓ Alert check complete: {fired} fired, {resolved} auto-resolved'
            )
        )

    def _notify_admins(self, rule, triggered_value, alert):
        from authentication.models import CustomUser
        from notifications.utils import create_notification

        admins = CustomUser.objects.filter(is_staff=True, is_active=True)
        severity_label = rule.severity.upper()

        for admin in admins:
            create_notification(
                user=admin,
                notification_type='account',
                title=f'[{severity_label}] {rule.name}',
                body=(
                    f'{rule.get_metric_type_display()} is {triggered_value} '
                    f'(threshold: {rule.get_condition_display().lower()} {rule.threshold_value})'
                ),
                action_url=f'/api/monitoring/alerts/{alert.pk}/',
            )
