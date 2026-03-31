from django.core.management.base import BaseCommand
from django.db.models import Sum
from django.utils import timezone


class Command(BaseCommand):
    help = 'Record current system metrics to the database'

    def handle(self, *args, **options):
        from monitoring.models import SystemMetric
        from billing.models import Invoice, Payment
        from property.models import Unit, TenantApplication
        from maintenance.models import MaintenanceRequest
        from disputes.models import Dispute

        now = timezone.now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        metrics = []

        # Overdue invoice count
        overdue_count = Invoice.objects.filter(status='overdue').count()
        metrics.append(('overdue_invoice_count', overdue_count))

        # Monthly revenue (completed payments this calendar month)
        monthly_revenue = (
            Payment.objects.filter(status='completed', created_at__gte=month_start)
            .aggregate(total=Sum('amount'))['total'] or 0
        )
        metrics.append(('monthly_revenue', monthly_revenue))

        # Platform-wide occupancy rate
        total_units = Unit.objects.count()
        occupied_units = Unit.objects.filter(is_occupied=True).count()
        occupancy_rate = round((occupied_units / total_units * 100), 2) if total_units > 0 else 0
        metrics.append(('occupancy_rate', occupancy_rate))

        # Open maintenance requests (not yet completed or cancelled/rejected)
        open_maintenance = MaintenanceRequest.objects.filter(
            status__in=['submitted', 'open', 'assigned', 'in_progress']
        ).count()
        metrics.append(('open_maintenance_count', open_maintenance))

        # Open disputes
        open_disputes = Dispute.objects.filter(status__in=['open', 'under_review']).count()
        metrics.append(('open_dispute_count', open_disputes))

        # Pending tenant applications
        pending_apps = TenantApplication.objects.filter(status='pending').count()
        metrics.append(('pending_application_count', pending_apps))

        # Payment success rate over the last 30 days
        since_30d = now - timezone.timedelta(days=30)
        total_payments = Payment.objects.filter(created_at__gte=since_30d).count()
        completed_payments = Payment.objects.filter(
            status='completed', created_at__gte=since_30d
        ).count()
        success_rate = (
            round(completed_payments / total_payments * 100, 2)
            if total_payments > 0
            else 100
        )
        metrics.append(('payment_success_rate', success_rate))

        SystemMetric.objects.bulk_create([
            SystemMetric(metric_type=mt, value=val) for mt, val in metrics
        ])

        self.stdout.write(
            self.style.SUCCESS(
                f'✓ Recorded {len(metrics)} metrics at {now.strftime("%Y-%m-%d %H:%M:%S")}'
            )
        )
        for mt, val in metrics:
            self.stdout.write(f'  {mt}: {val}')
