from decimal import Decimal

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
        fields = ['id', 'lease', 'period_start', 'period_end', 'due_date',
                  'rent_amount', 'late_fee_amount', 'total_amount', 'status',
                  'amount_paid', 'created_at']
        read_only_fields = ['rent_amount', 'late_fee_amount', 'total_amount', 'status', 'created_at']

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


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ['id', 'invoice', 'amount', 'stripe_payment_intent_id',
                  'stripe_charge_id', 'status', 'paid_at', 'created_at']
        read_only_fields = ['stripe_payment_intent_id', 'stripe_charge_id', 'status', 'paid_at', 'created_at']


class ReceiptSerializer(serializers.ModelSerializer):
    class Meta:
        model = Receipt
        fields = ['id', 'payment', 'receipt_number', 'issued_at']


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
