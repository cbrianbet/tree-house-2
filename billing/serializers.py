from rest_framework import serializers
from .models import BillingConfig, Invoice, Payment, Receipt, ReminderLog, ChargeType, AdditionalIncome, Expense


class BillingConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = BillingConfig
        fields = ['id', 'property', 'rent_due_day', 'grace_period_days',
                  'late_fee_percentage', 'late_fee_max_percentage', 'updated_at', 'updated_by']
        read_only_fields = ['property', 'updated_at', 'updated_by']

    def validate_rent_due_day(self, value):
        if not (1 <= value <= 28):
            raise serializers.ValidationError("rent_due_day must be between 1 and 28.")
        return value


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
        fields = ['id', 'property', 'name', 'created_by', 'created_at']
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
