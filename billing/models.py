from django.db import models
from django.utils import timezone
from authentication.models import CustomUser
from property.models import Property, Unit, Lease
from billing.utils import generate_invoice_number


class BillingConfig(models.Model):
    LATE_FEE_MODE_PERCENTAGE = 'percentage'
    LATE_FEE_MODE_FIXED = 'fixed'
    LATE_FEE_MODE_CHOICES = [
        (LATE_FEE_MODE_PERCENTAGE, 'Percentage'),
        (LATE_FEE_MODE_FIXED, 'Fixed'),
    ]

    property = models.OneToOneField(Property, on_delete=models.CASCADE, related_name='billing_config')
    rent_due_day = models.PositiveIntegerField(help_text="Day of month rent is due (1-28)")
    grace_period_days = models.PositiveIntegerField(default=0, help_text="Days after due date before late fee applies")
    late_fee_percentage = models.DecimalField(max_digits=5, decimal_places=2, help_text="Late fee as % of rent amount")
    late_fee_max_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text="Cap on total late fees as % of rent")
    invoice_lead_days = models.PositiveSmallIntegerField(
        default=0,
        help_text="Days before rent_due_day to generate invoice (0 = on due day).",
    )
    late_fee_mode = models.CharField(
        max_length=20, choices=LATE_FEE_MODE_CHOICES, default=LATE_FEE_MODE_PERCENTAGE,
    )
    late_fee_fixed_amount = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
    )
    mpesa_paybill = models.CharField(max_length=50, blank=True)
    mpesa_account_label = models.CharField(max_length=100, blank=True)
    bank_name = models.CharField(max_length=200, blank=True)
    bank_account = models.CharField(max_length=100, blank=True)
    payment_notes = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"BillingConfig for {self.property.name}"


class PropertyBillingNotificationSettings(models.Model):
    """Per-property billing email/in-app reminder behavior (optional row)."""

    property = models.OneToOneField(
        Property, on_delete=models.CASCADE, related_name='billing_notification_settings',
    )
    remind_before_due_days = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text="Days before due_date for pre-due reminder; null disables. If no settings row, legacy 3 applies.",
    )
    remind_after_overdue_days = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text="Days after due_date before overdue reminder; null treats as 0 (as soon as overdue).",
    )
    send_receipt_on_payment = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Property billing notification settings'
        verbose_name_plural = 'Property billing notification settings'

    def __str__(self):
        return f"BillingNotificationSettings({self.property.name})"


class Invoice(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('partial', 'Partial'),
        ('overdue', 'Overdue'),
        ('cancelled', 'Cancelled'),
    ]

    lease = models.ForeignKey(Lease, on_delete=models.CASCADE, related_name='invoices')
    invoice_number = models.CharField(max_length=32, unique=True, blank=True, db_index=True)
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

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.invoice_number:
            self.invoice_number = generate_invoice_number(self.pk)
            type(self).objects.filter(pk=self.pk).update(invoice_number=self.invoice_number)

    def __str__(self):
        return f"Invoice {self.invoice_number or self.id} — {self.lease.unit} ({self.period_start})"

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
    PAYMENT_METHOD_MPESA = 'mpesa'
    PAYMENT_METHOD_BANK = 'bank'
    PAYMENT_METHOD_CARD = 'card'
    PAYMENT_METHOD_CASH = 'cash'
    PAYMENT_METHOD_OTHER = 'other'
    PAYMENT_METHOD_CHOICES = [
        (PAYMENT_METHOD_MPESA, 'M-Pesa'),
        (PAYMENT_METHOD_BANK, 'Bank'),
        (PAYMENT_METHOD_CARD, 'Card'),
        (PAYMENT_METHOD_CASH, 'Cash'),
        (PAYMENT_METHOD_OTHER, 'Other'),
    ]

    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    stripe_payment_intent_id = models.CharField(max_length=200, unique=True)
    stripe_charge_id = models.CharField(max_length=200, blank=True)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default=PAYMENT_METHOD_OTHER)
    transaction_reference = models.CharField(max_length=128, blank=True, null=True, db_index=True)
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


class ChargeType(models.Model):
    """Landlord-defined income categories per property (water, electricity, service charge, etc.)."""

    KIND_FIXED = 'fixed'
    KIND_VARIABLE = 'variable'
    KIND_PER_UNIT = 'per_unit'
    CHARGE_KIND_CHOICES = [
        (KIND_FIXED, 'Fixed'),
        (KIND_VARIABLE, 'Variable'),
        (KIND_PER_UNIT, 'Per unit'),
    ]

    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='charge_types')
    name = models.CharField(max_length=100)
    charge_kind = models.CharField(
        max_length=20, choices=CHARGE_KIND_CHOICES, default=KIND_VARIABLE,
    )
    default_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    description = models.TextField(blank=True)
    display_order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='created_charge_types')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('property', 'name')

    def __str__(self):
        return f"{self.name} ({self.property.name})"


class AdditionalIncome(models.Model):
    """Income from landlord-defined charges billed to a unit (water, electricity, etc.)."""
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE, related_name='additional_income')
    charge_type = models.ForeignKey(ChargeType, on_delete=models.CASCADE, related_name='income_entries')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateField()
    description = models.TextField(blank=True)
    recorded_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='recorded_income')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.charge_type.name} — {self.unit} — {self.amount}"


class Expense(models.Model):
    """Costs incurred by the landlord for a property or unit."""
    CATEGORY_CHOICES = [
        ('maintenance', 'Maintenance'),
        ('utility', 'Utility'),
        ('insurance', 'Insurance'),
        ('tax', 'Tax'),
        ('repair', 'Repair'),
        ('management_fee', 'Management Fee'),
        ('other', 'Other'),
    ]

    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='expenses')
    unit = models.ForeignKey(Unit, null=True, blank=True, on_delete=models.SET_NULL, related_name='expenses')
    maintenance_request = models.ForeignKey(
        'maintenance.MaintenanceRequest', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='expenses',
    )
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField(blank=True)
    date = models.DateField()
    recorded_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='recorded_expenses')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.get_category_display()} — {self.property.name} — {self.amount}"
