from decimal import Decimal

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers
from property.models import Lease

from .models import (
    BillingConfig,
    Invoice,
    Payment,
    Receipt,
    ReminderLog,
    ChargeType,
    AdditionalIncome,
    Expense,
    PropertyBillingNotificationSettings,
)


class PropertyBillingNotificationSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = PropertyBillingNotificationSettings
        fields = [
            'remind_before_due_days',
            'remind_after_overdue_days',
            'send_receipt_on_payment',
        ]


class BillingConfigSerializer(serializers.ModelSerializer):
    notification_settings = PropertyBillingNotificationSettingsSerializer(
        required=False, write_only=True,
    )

    class Meta:
        model = BillingConfig
        fields = [
            'id', 'property', 'rent_due_day', 'grace_period_days',
            'late_fee_percentage', 'late_fee_max_percentage',
            'invoice_lead_days', 'late_fee_mode', 'late_fee_fixed_amount',
            'mpesa_paybill', 'mpesa_account_label', 'bank_name', 'bank_account', 'payment_notes',
            'notification_settings',
            'updated_at', 'updated_by',
        ]
        read_only_fields = ['property', 'updated_at', 'updated_by']

    def validate_rent_due_day(self, value):
        if not (1 <= value <= 28):
            raise serializers.ValidationError("rent_due_day must be between 1 and 28.")
        return value

    def validate_invoice_lead_days(self, value):
        if value > 27:
            raise serializers.ValidationError("invoice_lead_days must be at most 27.")
        return value

    def validate(self, attrs):
        instance = self.instance
        mode = attrs.get('late_fee_mode', getattr(instance, 'late_fee_mode', None) if instance else BillingConfig.LATE_FEE_MODE_PERCENTAGE)
        if mode is None:
            mode = BillingConfig.LATE_FEE_MODE_PERCENTAGE

        fixed = attrs.get('late_fee_fixed_amount', getattr(instance, 'late_fee_fixed_amount', None) if instance else None)

        if mode == BillingConfig.LATE_FEE_MODE_FIXED:
            if fixed is None or fixed == '':
                raise serializers.ValidationError({
                    'late_fee_fixed_amount': 'This field is required when late_fee_mode is fixed.',
                })
        elif mode == BillingConfig.LATE_FEE_MODE_PERCENTAGE:
            attrs['late_fee_fixed_amount'] = None

        return attrs

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['configured'] = True
        try:
            ns = instance.property.billing_notification_settings
            data['notification_settings'] = PropertyBillingNotificationSettingsSerializer(ns).data
        except PropertyBillingNotificationSettings.DoesNotExist:
            data['notification_settings'] = None
        return data

    def create(self, validated_data):
        notification_data = validated_data.pop('notification_settings', None)
        config = super().create(validated_data)
        if notification_data is not None:
            PropertyBillingNotificationSettings.objects.update_or_create(
                property=config.property,
                defaults=notification_data,
            )
        return config

    def update(self, instance, validated_data):
        notification_data = validated_data.pop('notification_settings', None)
        config = super().update(instance, validated_data)
        if notification_data is not None:
            PropertyBillingNotificationSettings.objects.update_or_create(
                property=config.property,
                defaults=notification_data,
            )
        return config


class InvoiceSerializer(serializers.ModelSerializer):
    amount_paid = serializers.SerializerMethodField()

    class Meta:
        model = Invoice
        fields = ['id', 'invoice_number', 'lease', 'period_start', 'period_end', 'due_date',
                  'rent_amount', 'late_fee_amount', 'total_amount', 'status',
                  'amount_paid', 'created_at']
        read_only_fields = ['invoice_number', 'rent_amount', 'late_fee_amount', 'total_amount', 'status', 'created_at']

    def get_amount_paid(self, obj):
        return str(obj.amount_paid())


class InvoiceCreateSerializer(serializers.Serializer):
    lease = serializers.PrimaryKeyRelatedField(
        queryset=Lease.objects.select_related('unit__property'),
    )
    period_start = serializers.DateField()
    period_end = serializers.DateField()
    due_date = serializers.DateField()
    rent_amount = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False, min_value=Decimal('0.01'),
    )

    def validate(self, data):
        lease = data['lease']
        if not lease.is_active:
            raise serializers.ValidationError({'lease': 'Lease must be active.'})

        period_start = data['period_start']
        period_end = data['period_end']
        if period_start > period_end:
            raise serializers.ValidationError({
                'period_end': 'period_end must be on or after period_start.',
            })

        if period_end < lease.start_date or (
            lease.end_date is not None and period_start > lease.end_date
        ):
            raise serializers.ValidationError({
                'period_start': 'Billing period does not overlap the lease.',
            })

        if data.get('rent_amount') is None:
            data['rent_amount'] = lease.rent_amount

        return data


class ManualPaymentRecordSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal('0.01'))
    payment_method = serializers.CharField(required=False, allow_blank=True, max_length=20)
    fee_amount = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        min_value=Decimal('0'),
        default=Decimal('0'),
    )
    transaction_reference = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        max_length=128,
    )

    def validate_payment_method(self, value):
        if value is None or not str(value).strip():
            return None
        v = str(value).strip().lower()
        allowed = {c[0] for c in Payment.PAYMENT_METHOD_CHOICES}
        if v not in allowed:
            raise serializers.ValidationError('Invalid choice.')
        return v


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = [
            'id', 'invoice', 'amount', 'fee_amount', 'stripe_payment_intent_id',
            'stripe_charge_id', 'payment_method', 'transaction_reference',
            'status', 'paid_at', 'created_at',
        ]
        read_only_fields = ['stripe_payment_intent_id', 'stripe_charge_id', 'status', 'paid_at', 'created_at']


_CHARGE_TYPE_NOT_ANNOTATED = object()


class ReceiptMethodBreakdownSerializer(serializers.Serializer):
    mpesa = serializers.FloatField(help_text='Share of receipts (%) paid with M-Pesa.')
    bank = serializers.FloatField(help_text='Share of receipts (%) paid by bank transfer.')
    card = serializers.FloatField(help_text='Share of receipts (%) paid by card.')
    cash = serializers.FloatField(help_text='Share of receipts (%) paid in cash.')
    other = serializers.FloatField(help_text='Share of receipts (%) with method "other".')


class ReceiptStatsSerializer(serializers.Serializer):
    total_count = serializers.IntegerField(help_text='Receipts after role scope and optional filters.')
    this_month_count = serializers.IntegerField(
        help_text='Subset of those receipts whose effective time falls in the current calendar month.',
    )
    this_month_total = serializers.CharField(
        help_text='Sum of payment amounts for `this_month_count` (decimal string, two places).',
    )
    method_breakdown = ReceiptMethodBreakdownSerializer(
        help_text='Percentage of receipts by payment method; keys are fixed; sums to ~100 when total_count > 0.',
    )
    average_amount = serializers.CharField(
        help_text='Mean payment amount over the filtered receipt set (decimal string, two places).',
    )


class ReceiptSerializer(serializers.ModelSerializer):
    amount = serializers.DecimalField(
        max_digits=10, decimal_places=2, source='payment.amount', read_only=True,
        help_text='Payment amount (decimal string).',
    )
    fee_amount = serializers.DecimalField(
        max_digits=10, decimal_places=2, source='payment.fee_amount', read_only=True,
        help_text='Per-payment fee if any; not counted toward invoice principal.',
    )
    payment_status = serializers.CharField(
        source='payment.status', read_only=True,
        help_text='Underlying payment status: pending, completed, or failed.',
    )
    paid_at = serializers.DateTimeField(
        source='payment.paid_at', read_only=True, allow_null=True,
        help_text='When the payment completed; null if not set.',
    )
    payment_method = serializers.CharField(
        source='payment.payment_method', read_only=True,
        help_text='mpesa | bank | card | cash | other',
    )
    transaction_ref = serializers.SerializerMethodField(
        help_text='Gateway reference: `transaction_reference` if set, else `stripe_charge_id`, else null.',
    )
    transaction_reference = serializers.SerializerMethodField(
        help_text='Same resolved reference as `transaction_ref` (duplicate for legacy clients).',
    )
    invoice_id = serializers.IntegerField(source='payment.invoice_id', read_only=True)
    invoice_number = serializers.CharField(source='payment.invoice.invoice_number', read_only=True)
    invoice_status = serializers.CharField(source='payment.invoice.status', read_only=True)
    invoice_period_start = serializers.DateField(
        source='payment.invoice.period_start', read_only=True,
    )
    invoice_period_end = serializers.DateField(
        source='payment.invoice.period_end', read_only=True,
    )
    tenant_id = serializers.IntegerField(
        source='payment.invoice.lease.tenant_id', read_only=True,
    )
    tenant_name = serializers.SerializerMethodField()
    tenant_email = serializers.CharField(
        source='payment.invoice.lease.tenant.email', read_only=True, allow_blank=True,
    )
    unit_id = serializers.IntegerField(
        source='payment.invoice.lease.unit_id', read_only=True,
    )
    unit_name = serializers.CharField(
        source='payment.invoice.lease.unit.name', read_only=True,
    )
    property_id = serializers.IntegerField(
        source='payment.invoice.lease.unit.property_id', read_only=True,
    )
    property_name = serializers.CharField(
        source='payment.invoice.lease.unit.property.name', read_only=True,
    )
    charge_type = serializers.SerializerMethodField(
        help_text="`Rent` or `Rent + Service` if additional income exists for the unit in the invoice period.",
    )

    class Meta:
        model = Receipt
        fields = [
            'id', 'payment', 'receipt_number', 'issued_at',
            'amount', 'fee_amount', 'payment_status', 'paid_at', 'payment_method',
            'transaction_ref', 'transaction_reference',
            'invoice_id', 'invoice_number', 'invoice_status',
            'invoice_period_start', 'invoice_period_end',
            'tenant_id', 'tenant_name', 'tenant_email',
            'unit_id', 'unit_name', 'property_id', 'property_name',
            'charge_type',
        ]

    @extend_schema_field({'type': 'string', 'nullable': True})
    def get_transaction_ref(self, obj):
        p = obj.payment
        ref = p.transaction_reference or p.stripe_charge_id
        return ref or None

    @extend_schema_field({'type': 'string', 'nullable': True})
    def get_transaction_reference(self, obj):
        return self.get_transaction_ref(obj)

    @extend_schema_field(serializers.CharField())
    def get_tenant_name(self, obj):
        u = obj.payment.invoice.lease.tenant
        name = f'{(u.first_name or "").strip()} {(u.last_name or "").strip()}'.strip()
        if name:
            return name
        if u.username:
            return u.username
        return u.email or ''

    @extend_schema_field(
        serializers.ChoiceField(choices=['Rent', 'Rent + Service']),
    )
    def get_charge_type(self, obj):
        flag = getattr(obj, 'has_service_income', _CHARGE_TYPE_NOT_ANNOTATED)
        if flag is _CHARGE_TYPE_NOT_ANNOTATED:
            return 'Rent + Service' if self._additional_income_in_invoice_period(obj) else 'Rent'
        return 'Rent + Service' if flag else 'Rent'

    @staticmethod
    def _additional_income_in_invoice_period(obj):
        inv = obj.payment.invoice
        return AdditionalIncome.objects.filter(
            unit_id=inv.lease.unit_id,
            date__gte=inv.period_start,
            date__lte=inv.period_end,
        ).exists()


class ReceiptListPaginatedSerializer(serializers.Serializer):
    """OpenAPI envelope for `GET /api/billing/receipts/` (matches DRF PageNumberPagination)."""

    count = serializers.IntegerField(help_text='Total receipts matching filters across all pages.')
    next = serializers.URLField(
        allow_null=True,
        required=False,
        help_text='URL of the next page, or null when none.',
    )
    previous = serializers.URLField(
        allow_null=True,
        required=False,
        help_text='URL of the previous page, or null when none.',
    )
    results = ReceiptSerializer(many=True)


class ReminderLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReminderLog
        fields = ['id', 'invoice', 'reminder_type', 'sent_at']


class ChargeTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChargeType
        fields = [
            'id', 'property', 'name', 'charge_kind', 'default_amount', 'description',
            'display_order', 'is_active', 'created_by', 'created_at',
        ]
        read_only_fields = ['property', 'created_by', 'created_at']


class AdditionalIncomeSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdditionalIncome
        fields = ['id', 'unit', 'charge_type', 'amount', 'date', 'description', 'recorded_by', 'created_at']
        read_only_fields = ['recorded_by', 'created_at']


class ExpenseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Expense
        fields = [
            'id', 'property', 'unit', 'maintenance_request', 'category',
            'amount', 'description', 'date', 'recorded_by', 'created_at',
        ]
        read_only_fields = ['property', 'maintenance_request', 'recorded_by', 'created_at']
