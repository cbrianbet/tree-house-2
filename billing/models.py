from django.db import models
from django.utils import timezone
from authentication.models import CustomUser
from property.models import Property, Lease


class BillingConfig(models.Model):
    property = models.OneToOneField(Property, on_delete=models.CASCADE, related_name='billing_config')
    rent_due_day = models.PositiveIntegerField(help_text="Day of month rent is due (1-28)")
    grace_period_days = models.PositiveIntegerField(default=0, help_text="Days after due date before late fee applies")
    late_fee_percentage = models.DecimalField(max_digits=5, decimal_places=2, help_text="Late fee as % of rent amount")
    late_fee_max_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text="Cap on total late fees as % of rent")
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"BillingConfig for {self.property.name}"


class Invoice(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('partial', 'Partial'),
        ('overdue', 'Overdue'),
        ('cancelled', 'Cancelled'),
    ]

    lease = models.ForeignKey(Lease, on_delete=models.CASCADE, related_name='invoices')
    period_start = models.DateField()
    period_end = models.DateField()
    due_date = models.DateField()
    rent_amount = models.DecimalField(max_digits=10, decimal_places=2)
    late_fee_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('lease', 'period_start')

    def __str__(self):
        return f"Invoice {self.id} — {self.lease.unit} ({self.period_start})"

    def amount_paid(self):
        return sum(p.amount for p in self.payments.filter(status='completed'))

    def update_status(self):
        paid = self.amount_paid()
        if paid >= self.total_amount:
            self.status = 'paid'
        elif paid > 0:
            self.status = 'partial'
        elif self.due_date < timezone.now().date() and self.status not in ('paid', 'cancelled'):
            self.status = 'overdue'
        self.save()


class Payment(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    stripe_payment_intent_id = models.CharField(max_length=200, unique=True)
    stripe_charge_id = models.CharField(max_length=200, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Payment {self.stripe_payment_intent_id} — {self.status}"


class Receipt(models.Model):
    payment = models.OneToOneField(Payment, on_delete=models.CASCADE, related_name='receipt')
    receipt_number = models.CharField(max_length=50, unique=True)
    issued_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.receipt_number


class ReminderLog(models.Model):
    REMINDER_TYPES = [
        ('pre_due', 'Pre Due'),
        ('due_date', 'Due Date'),
        ('overdue', 'Overdue'),
    ]

    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='reminders')
    reminder_type = models.CharField(max_length=20, choices=REMINDER_TYPES)
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('invoice', 'reminder_type')

    def __str__(self):
        return f"{self.reminder_type} reminder for Invoice {self.invoice_id}"
