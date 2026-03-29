import calendar
from datetime import date, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone

from property.models import Lease
from billing.models import BillingConfig, Invoice, ReminderLog


class Command(BaseCommand):
    help = 'Generate invoices, apply late fees, and send email reminders'

    def handle(self, *args, **options):
        today = timezone.now().date()
        self._generate_invoices(today)
        self._apply_late_fees(today)
        self._send_reminders(today)

    # ── Invoice Generation ──────────────────────────────────────────────────────

    def _generate_invoices(self, today):
        active_leases = Lease.objects.filter(
            is_active=True
        ).select_related('unit__property__billing_config', 'tenant')

        for lease in active_leases:
            try:
                config = lease.unit.property.billing_config
            except BillingConfig.DoesNotExist:
                self.stdout.write(f'  No billing config for property "{lease.unit.property.name}" — skipping')
                continue

            due_day = self._clamp_due_day(config.rent_due_day, today.year, today.month)
            if today.day != due_day:
                continue

            period_start = today.replace(day=1)
            period_end = today.replace(day=calendar.monthrange(today.year, today.month)[1])
            due_date = today + timedelta(days=config.grace_period_days)

            _, created = Invoice.objects.get_or_create(
                lease=lease,
                period_start=period_start,
                defaults={
                    'period_end': period_end,
                    'due_date': due_date,
                    'rent_amount': lease.rent_amount,
                    'late_fee_amount': Decimal('0'),
                    'total_amount': lease.rent_amount,
                    'status': 'pending',
                },
            )
            if created:
                self.stdout.write(self.style.SUCCESS(
                    f'  Created invoice for {lease.tenant.username} — {lease.unit} ({period_start})'
                ))

    # ── Late Fees ───────────────────────────────────────────────────────────────

    def _apply_late_fees(self, today):
        overdue_invoices = Invoice.objects.filter(
            status__in=['pending', 'partial'],
            due_date__lt=today,
        ).select_related('lease__unit__property__billing_config')

        for invoice in overdue_invoices:
            try:
                config = invoice.lease.unit.property.billing_config
            except BillingConfig.DoesNotExist:
                continue

            late_fee = (invoice.rent_amount * config.late_fee_percentage / Decimal('100')).quantize(Decimal('0.01'))

            if config.late_fee_max_percentage:
                max_fee = (invoice.rent_amount * config.late_fee_max_percentage / Decimal('100')).quantize(Decimal('0.01'))
                late_fee = min(late_fee, max_fee)

            invoice.late_fee_amount = late_fee
            invoice.total_amount = invoice.rent_amount + late_fee
            invoice.status = 'overdue'
            invoice.save()

            self.stdout.write(self.style.WARNING(
                f'  Late fee applied: {invoice.lease.tenant.username} — Invoice {invoice.id} (+{late_fee})'
            ))

    # ── Email Reminders ─────────────────────────────────────────────────────────

    def _send_reminders(self, today):
        self._send_pre_due_reminders(today)
        self._send_due_date_reminders(today)
        self._send_overdue_reminders()

    def _send_pre_due_reminders(self, today):
        target_due = today + timedelta(days=3)
        invoices = Invoice.objects.filter(
            due_date=target_due,
            status__in=['pending', 'partial'],
        ).exclude(reminders__reminder_type='pre_due').select_related('lease__tenant')

        for invoice in invoices:
            tenant = invoice.lease.tenant
            send_mail(
                subject='Rent due in 3 days',
                message=(
                    f'Hi {tenant.first_name or tenant.username},\n\n'
                    f'This is a reminder that your rent of KES {invoice.total_amount} '
                    f'is due on {invoice.due_date}.\n\n'
                    f'Invoice #{invoice.id} | Period: {invoice.period_start} – {invoice.period_end}\n\n'
                    f'Please ensure payment is made on time to avoid late fees.\n\n'
                    f'Tree House'
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[tenant.email],
                fail_silently=True,
            )
            ReminderLog.objects.create(invoice=invoice, reminder_type='pre_due')
            self.stdout.write(f'  Pre-due reminder sent to {tenant.email}')

    def _send_due_date_reminders(self, today):
        invoices = Invoice.objects.filter(
            due_date=today,
            status__in=['pending', 'partial'],
        ).exclude(reminders__reminder_type='due_date').select_related('lease__tenant')

        for invoice in invoices:
            tenant = invoice.lease.tenant
            send_mail(
                subject='Rent is due today',
                message=(
                    f'Hi {tenant.first_name or tenant.username},\n\n'
                    f'Your rent of KES {invoice.total_amount} is due today ({invoice.due_date}).\n\n'
                    f'Invoice #{invoice.id} | Period: {invoice.period_start} – {invoice.period_end}\n\n'
                    f'Please make payment today to avoid late fees.\n\n'
                    f'Tree House'
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[tenant.email],
                fail_silently=True,
            )
            ReminderLog.objects.create(invoice=invoice, reminder_type='due_date')
            self.stdout.write(f'  Due-date reminder sent to {tenant.email}')

    def _send_overdue_reminders(self):
        invoices = Invoice.objects.filter(
            status='overdue',
        ).exclude(reminders__reminder_type='overdue').select_related('lease__tenant')

        for invoice in invoices:
            tenant = invoice.lease.tenant
            send_mail(
                subject='Rent overdue — late fee applied',
                message=(
                    f'Hi {tenant.first_name or tenant.username},\n\n'
                    f'Your rent for the period {invoice.period_start} – {invoice.period_end} is overdue.\n\n'
                    f'Rent:      KES {invoice.rent_amount}\n'
                    f'Late fee:  KES {invoice.late_fee_amount}\n'
                    f'Total due: KES {invoice.total_amount}\n\n'
                    f'Please make payment immediately to avoid further charges.\n\n'
                    f'Tree House'
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[tenant.email],
                fail_silently=True,
            )
            ReminderLog.objects.create(invoice=invoice, reminder_type='overdue')
            self.stdout.write(self.style.ERROR(f'  Overdue reminder sent to {tenant.email}'))

    # ── Helpers ─────────────────────────────────────────────────────────────────

    def _clamp_due_day(self, due_day, year, month):
        """Return due_day clamped to the last day of the given month."""
        max_day = calendar.monthrange(year, month)[1]
        return min(due_day, max_day)
