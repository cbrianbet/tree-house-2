import calendar
import json
import uuid
import stripe
from datetime import date, timedelta

from django.conf import settings
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema, OpenApiExample

from decimal import Decimal

from django.db import IntegrityError, transaction
from django.db.models import Sum, Count, Q

from property.models import Property, Unit, Lease
from property.views import is_admin, is_landlord, is_agent_for
from .models import (
    BillingConfig,
    Invoice,
    Payment,
    Receipt,
    ChargeType,
    AdditionalIncome,
    Expense,
    PropertyBillingNotificationSettings,
)
from .serializers import (
    BillingConfigSerializer, InvoiceSerializer, InvoiceCreateSerializer,
    ManualPaymentRecordSerializer,
    PaymentSerializer, ReceiptSerializer,
    ChargeTypeSerializer, AdditionalIncomeSerializer, ExpenseSerializer,
)
from .utils import generate_receipt_number

stripe.api_key = settings.STRIPE_SECRET_KEY


def _units_reporting_qs(prop):
    return Unit.objects.filter(property=prop, deleted_at__isnull=True)


def _occupancy_for_period(prop, period_start, period_end):
    """
    Units with a lease overlapping [period_start, period_end] (inclusive),
    over non-deleted units on the property. Percent is two decimal places.
    """
    total = _units_reporting_qs(prop).count()
    if total == 0:
        return {
            'occupied_units': 0,
            'total_units': 0,
            'occupancy_pct': None,
        }
    occupied = (
        Lease.objects.filter(
            unit__property=prop,
            unit__deleted_at__isnull=True,
            start_date__lte=period_end,
        )
        .filter(Q(end_date__isnull=True) | Q(end_date__gte=period_start))
        .count()
    )
    pct = (Decimal(occupied) / Decimal(total) * Decimal('100')).quantize(Decimal('0.01'))
    return {
        'occupied_units': occupied,
        'total_units': total,
        'occupancy_pct': str(pct),
    }


def _property_sends_receipt_on_payment(prop):
    try:
        return prop.billing_notification_settings.send_receipt_on_payment
    except PropertyBillingNotificationSettings.DoesNotExist:
        return True


def _notify_tenant_payment_received(invoice, amount, receipt_number):
    if not _property_sends_receipt_on_payment(invoice.lease.unit.property):
        return
    from notifications.utils import create_notification

    tenant = invoice.lease.tenant
    create_notification(
        tenant,
        'payment',
        'Payment received',
        (
            f'Hi {tenant.first_name or tenant.username},\n\n'
            f'We recorded a payment of KES {amount} toward invoice #{invoice.id}.\n'
            f'Receipt: {receipt_number}\n\n'
            f'Tree House'
        ),
        action_url='',
    )


def _billing_clamp_due_day(due_day, year, month):
    return min(due_day, calendar.monthrange(year, month)[1])


def _next_invoice_generation_on_or_after(start, rent_due_day, lead_days):
    for i in range(370):
        d = start + timedelta(days=i)
        cd = _billing_clamp_due_day(rent_due_day, d.year, d.month)
        gen_d = max(1, cd - lead_days)
        if d.day == gen_d:
            return d
    return None


def _next_rent_anchor_from_gen(gen_date, rent_due_day):
    cd = _billing_clamp_due_day(rent_due_day, gen_date.year, gen_date.month)
    return date(gen_date.year, gen_date.month, cd)


# ── Billing Config ─────────────────────────────────────────────────────────────

@extend_schema(methods=['GET'], summary="Get billing config for a property")
@extend_schema(
    methods=['POST'],
    summary="Create or update billing config for a property",
    examples=[
        OpenApiExample("Set billing config", request_only=True, value={
            "rent_due_day": 5,
            "grace_period_days": 3,
            "late_fee_percentage": "5.00",
            "late_fee_max_percentage": "20.00",
            "invoice_lead_days": 0,
            "late_fee_mode": "percentage",
            "late_fee_fixed_amount": None,
            "mpesa_paybill": "123456",
            "mpesa_account_label": "Unit code + phone",
            "bank_name": "Example Bank",
            "bank_account": "0123456789",
            "payment_notes": "Reference: invoice number",
            "notification_settings": {
                "remind_before_due_days": 3,
                "remind_after_overdue_days": 0,
                "send_receipt_on_payment": True,
            },
        })
    ],
)
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def billing_config(request, property_id):
    try:
        property = Property.objects.get(pk=property_id)
    except Property.DoesNotExist:
        return Response({'detail': 'Property not found.'}, status=status.HTTP_404_NOT_FOUND)

    can_read = is_admin(request.user) or property.owner == request.user or is_agent_for(request.user, property)
    can_write = is_admin(request.user) or property.owner == request.user

    if not can_read:
        return Response({'detail': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)

    if request.method == 'GET':
        try:
            config = property.billing_config
            return Response(BillingConfigSerializer(config).data)
        except BillingConfig.DoesNotExist:
            return Response({
                'configured': False,
                'property': property.id,
                'rent_due_day': 1,
                'grace_period_days': 0,
                'late_fee_percentage': '0.00',
                'late_fee_max_percentage': None,
                'invoice_lead_days': 0,
                'late_fee_mode': BillingConfig.LATE_FEE_MODE_PERCENTAGE,
                'late_fee_fixed_amount': None,
                'mpesa_paybill': '',
                'mpesa_account_label': '',
                'bank_name': '',
                'bank_account': '',
                'payment_notes': '',
                'notification_settings': None,
            })

    elif request.method == 'POST':
        if not can_write:
            return Response({'detail': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)
        try:
            config = property.billing_config
            serializer = BillingConfigSerializer(config, data=request.data, partial=True)
        except BillingConfig.DoesNotExist:
            serializer = BillingConfigSerializer(data=request.data)

        if serializer.is_valid():
            instance = serializer.save(property=property, updated_by=request.user)
            return Response(BillingConfigSerializer(instance).data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ── Invoices ───────────────────────────────────────────────────────────────────

@extend_schema(methods=['GET'], summary="List invoices")
@extend_schema(
    methods=['POST'],
    summary="Create invoice manually",
    examples=[
        OpenApiExample(
            "Create invoice",
            request_only=True,
            value={
                'lease': 1,
                'period_start': '2026-04-01',
                'period_end': '2026-04-30',
                'due_date': '2026-04-05',
                'rent_amount': '45000.00',
            },
        ),
    ],
)
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def invoice_list(request):
    user = request.user

    if request.method == 'GET':
        if is_admin(user):
            invoices = Invoice.objects.select_related('lease__unit__property').all()
        elif is_landlord(user):
            invoices = Invoice.objects.filter(lease__unit__property__owner=user)
        elif hasattr(user, 'role') and user.role.name == 'Agent':
            from property.models import PropertyAgent
            assigned_ids = PropertyAgent.objects.filter(agent=user).values_list('property_id', flat=True)
            invoices = Invoice.objects.filter(lease__unit__property_id__in=assigned_ids)
        else:
            # Tenant sees their own invoices
            invoices = Invoice.objects.filter(lease__tenant=user)

        serializer = InvoiceSerializer(invoices, many=True)
        return Response(serializer.data)

    serializer = InvoiceCreateSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    lease = serializer.validated_data['lease']
    prop = lease.unit.property
    can_create = is_admin(user) or prop.owner == user or is_agent_for(user, prop)
    if not can_create:
        return Response({'detail': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)

    try:
        prop.billing_config
    except BillingConfig.DoesNotExist:
        return Response(
            {'detail': 'No billing config set for this property.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        invoice = Invoice.objects.create(
            lease=lease,
            period_start=serializer.validated_data['period_start'],
            period_end=serializer.validated_data['period_end'],
            due_date=serializer.validated_data['due_date'],
            rent_amount=serializer.validated_data['rent_amount'],
            late_fee_amount=Decimal('0'),
            total_amount=serializer.validated_data['rent_amount'],
            status='pending',
        )
    except IntegrityError:
        return Response(
            {'detail': 'An invoice for this lease and period_start already exists.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    return Response(InvoiceSerializer(invoice).data, status=status.HTTP_201_CREATED)


@extend_schema(methods=['GET'], summary="Get invoice detail")
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def invoice_detail(request, pk):
    try:
        invoice = Invoice.objects.select_related('lease__unit__property').get(pk=pk)
    except Invoice.DoesNotExist:
        return Response({'detail': 'Invoice not found.'}, status=status.HTTP_404_NOT_FOUND)

    user = request.user
    prop = invoice.lease.unit.property
    is_tenant = invoice.lease.tenant == user
    has_access = is_admin(user) or prop.owner == user or is_agent_for(user, prop) or is_tenant

    if not has_access:
        return Response({'detail': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)

    return Response(InvoiceSerializer(invoice).data)


# ── Payments ───────────────────────────────────────────────────────────────────

@extend_schema(
    methods=['POST'],
    summary="Initiate a Stripe payment for an invoice",
    examples=[
        OpenApiExample("Pay invoice", request_only=True, value={"amount": "45000.00"})
    ],
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def pay_invoice(request, pk):
    try:
        invoice = Invoice.objects.select_related('lease__unit__property').get(pk=pk)
    except Invoice.DoesNotExist:
        return Response({'detail': 'Invoice not found.'}, status=status.HTTP_404_NOT_FOUND)

    if invoice.lease.tenant != request.user:
        return Response({'detail': 'Only the tenant can pay this invoice.'}, status=status.HTTP_403_FORBIDDEN)

    if invoice.status == 'paid':
        return Response({'detail': 'Invoice is already paid.'}, status=status.HTTP_400_BAD_REQUEST)

    if invoice.status == 'cancelled':
        return Response({'detail': 'Invoice is cancelled.'}, status=status.HTTP_400_BAD_REQUEST)

    amount_requested = request.data.get('amount')
    if not amount_requested:
        return Response({'detail': 'amount is required.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        amount_cents = int(float(amount_requested) * 100)
    except (ValueError, TypeError):
        return Response({'detail': 'Invalid amount.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        intent = stripe.PaymentIntent.create(
            amount=amount_cents,
            currency='kes',
            metadata={
                'invoice_id': invoice.id,
                'tenant': request.user.username,
            },
        )
    except stripe.error.StripeError as e:
        return Response({'detail': str(e)}, status=status.HTTP_502_BAD_GATEWAY)

    Payment.objects.create(
        invoice=invoice,
        amount=amount_requested,
        stripe_payment_intent_id=intent.id,
    )

    return Response({'client_secret': intent.client_secret}, status=status.HTTP_201_CREATED)


@extend_schema(methods=['GET'], summary="List payments for an invoice")
@extend_schema(
    methods=['POST'],
    summary="Record a manual payment (cash, bank transfer, etc.)",
    examples=[
        OpenApiExample(
            "Record manual payment",
            request_only=True,
            value={'amount': '25000.00'},
        ),
    ],
)
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def invoice_payments(request, pk):
    try:
        invoice = Invoice.objects.select_related('lease__unit__property').get(pk=pk)
    except Invoice.DoesNotExist:
        return Response({'detail': 'Invoice not found.'}, status=status.HTTP_404_NOT_FOUND)

    user = request.user
    prop = invoice.lease.unit.property
    is_tenant = invoice.lease.tenant == user
    if not (is_admin(user) or prop.owner == user or is_agent_for(user, prop) or is_tenant):
        return Response({'detail': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)

    if request.method == 'GET':
        payments = invoice.payments.all()
        return Response(PaymentSerializer(payments, many=True).data)

    if not (is_admin(user) or prop.owner == user or is_agent_for(user, prop)):
        return Response({'detail': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)

    if invoice.status == 'cancelled':
        return Response({'detail': 'Invoice is cancelled.'}, status=status.HTTP_400_BAD_REQUEST)

    serializer = ManualPaymentRecordSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    amount = serializer.validated_data['amount']
    remaining = invoice.total_amount - invoice.amount_paid()
    if remaining <= 0:
        return Response(
            {'detail': 'Invoice balance is already fully paid.'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if amount > remaining:
        return Response(
            {'detail': f'Amount exceeds remaining balance ({remaining}).'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    manual_ref = f'manual-{uuid.uuid4().hex}'
    try:
        with transaction.atomic():
            payment = Payment.objects.create(
                invoice=invoice,
                amount=amount,
                stripe_payment_intent_id=manual_ref,
                status='completed',
                paid_at=timezone.now(),
            )
            invoice.update_status()
            receipt = Receipt.objects.create(
                payment=payment,
                receipt_number=generate_receipt_number(),
            )
            _notify_tenant_payment_received(invoice, amount, receipt.receipt_number)
    except IntegrityError:
        return Response(
            {'detail': 'Could not record payment. Try again.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    return Response(
        {
            'payment': PaymentSerializer(payment).data,
            'receipt': ReceiptSerializer(receipt).data,
        },
        status=status.HTTP_201_CREATED,
    )


# ── Stripe Webhook ─────────────────────────────────────────────────────────────

@extend_schema(exclude=True)
@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE', '')

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except (ValueError, stripe.error.SignatureVerificationError):
        return Response({'detail': 'Invalid payload or signature.'}, status=status.HTTP_400_BAD_REQUEST)

    if event['type'] == 'payment_intent.succeeded':
        intent = event['data']['object']
        _handle_payment_success(intent)

    elif event['type'] == 'payment_intent.payment_failed':
        intent = event['data']['object']
        _handle_payment_failure(intent)

    return Response({'status': 'ok'})


def _handle_payment_success(intent):
    try:
        payment = Payment.objects.get(stripe_payment_intent_id=intent['id'])
    except Payment.DoesNotExist:
        return

    payment.status = 'completed'
    payment.paid_at = timezone.now()
    payment.stripe_charge_id = intent.get('latest_charge', '')
    payment.save()

    payment.invoice.update_status()

    # Auto-generate receipt
    if not hasattr(payment, 'receipt'):
        receipt = Receipt.objects.create(
            payment=payment,
            receipt_number=generate_receipt_number(),
        )
        _notify_tenant_payment_received(payment.invoice, payment.amount, receipt.receipt_number)


def _handle_payment_failure(intent):
    try:
        payment = Payment.objects.get(stripe_payment_intent_id=intent['id'])
    except Payment.DoesNotExist:
        return

    payment.status = 'failed'
    payment.save()


# ── Receipts ───────────────────────────────────────────────────────────────────

@extend_schema(methods=['GET'], summary="List receipts")
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def receipt_list(request):
    user = request.user
    if is_admin(user):
        receipts = Receipt.objects.select_related('payment__invoice__lease').all()
    elif is_landlord(user):
        receipts = Receipt.objects.filter(payment__invoice__lease__unit__property__owner=user)
    elif hasattr(user, 'role') and user.role.name == 'Agent':
        from property.models import PropertyAgent
        assigned_ids = PropertyAgent.objects.filter(agent=user).values_list('property_id', flat=True)
        receipts = Receipt.objects.filter(payment__invoice__lease__unit__property_id__in=assigned_ids)
    else:
        receipts = Receipt.objects.filter(payment__invoice__lease__tenant=user)

    return Response(ReceiptSerializer(receipts, many=True).data)


@extend_schema(methods=['GET'], summary="Get receipt detail")
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def receipt_detail(request, pk):
    try:
        receipt = Receipt.objects.select_related('payment__invoice__lease__unit__property').get(pk=pk)
    except Receipt.DoesNotExist:
        return Response({'detail': 'Receipt not found.'}, status=status.HTTP_404_NOT_FOUND)

    user = request.user
    prop = receipt.payment.invoice.lease.unit.property
    is_tenant = receipt.payment.invoice.lease.tenant == user
    if not (is_admin(user) or prop.owner == user or is_agent_for(user, prop) or is_tenant):
        return Response({'detail': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)

    return Response(ReceiptSerializer(receipt).data)


# ── Charge Types ────────────────────────────────────────────────────────────────

@extend_schema(methods=['GET'], summary="List charge types for a property")
@extend_schema(
    methods=['POST'],
    summary="Create a charge type for a property (landlord/admin only)",
    examples=[
        OpenApiExample("Water charge", request_only=True, value={"name": "Water"}),
        OpenApiExample("Electricity charge", request_only=True, value={"name": "Electricity"}),
        OpenApiExample("Service charge", request_only=True, value={"name": "Service Charge"}),
    ],
)
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def charge_type_list_create(request, property_pk):
    try:
        prop = Property.objects.get(pk=property_pk)
    except Property.DoesNotExist:
        return Response({'detail': 'Property not found.'}, status=status.HTTP_404_NOT_FOUND)

    user = request.user
    if not (is_admin(user) or prop.owner == user or is_agent_for(user, prop)):
        return Response({'detail': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)

    if request.method == 'GET':
        qs = prop.charge_types.all().order_by('display_order', 'id')
        if request.query_params.get('include_inactive') not in ('1', 'true', 'yes'):
            qs = qs.filter(is_active=True)
        return Response(ChargeTypeSerializer(qs, many=True).data)

    elif request.method == 'POST':
        if not (is_admin(user) or prop.owner == user):
            return Response({'detail': 'Only the property owner can create charge types.'}, status=status.HTTP_403_FORBIDDEN)
        serializer = ChargeTypeSerializer(data=request.data)
        if serializer.is_valid():
            try:
                serializer.save(property=prop, created_by=user)
            except IntegrityError:
                return Response(
                    {'detail': 'A charge type with this name already exists for this property.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(methods=['GET'], summary="Get charge type detail")
@extend_schema(
    methods=['PUT'],
    summary="Update a charge type",
    examples=[OpenApiExample("Rename", request_only=True, value={"name": "Garbage Collection"})],
)
@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def charge_type_detail(request, property_pk, pk):
    try:
        prop = Property.objects.get(pk=property_pk)
    except Property.DoesNotExist:
        return Response({'detail': 'Property not found.'}, status=status.HTTP_404_NOT_FOUND)

    try:
        charge_type = ChargeType.objects.get(pk=pk, property=prop)
    except ChargeType.DoesNotExist:
        return Response({'detail': 'Charge type not found.'}, status=status.HTTP_404_NOT_FOUND)

    user = request.user
    if not (is_admin(user) or prop.owner == user or is_agent_for(user, prop)):
        return Response({'detail': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)

    if request.method == 'GET':
        return Response(ChargeTypeSerializer(charge_type).data)

    if not (is_admin(user) or prop.owner == user):
        return Response({'detail': 'Only the property owner can modify charge types.'}, status=status.HTTP_403_FORBIDDEN)

    if request.method == 'PUT':
        serializer = ChargeTypeSerializer(charge_type, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'DELETE':
        if AdditionalIncome.objects.filter(charge_type=charge_type).exists():
            return Response(
                {'detail': 'Charge type has income entries; set is_active=false instead of deleting.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        charge_type.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ── Additional Income ───────────────────────────────────────────────────────────

@extend_schema(methods=['GET'], summary="List additional income entries for a property")
@extend_schema(
    methods=['POST'],
    summary="Record additional income for a unit (water, electricity, service charge, etc.)",
    examples=[
        OpenApiExample("Water bill", request_only=True, value={
            "unit": 2,
            "charge_type": 1,
            "amount": "1500.00",
            "date": "2024-03-01",
            "description": "March water reading: 12 units",
        }),
    ],
)
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def additional_income_list_create(request, property_pk):
    try:
        prop = Property.objects.get(pk=property_pk)
    except Property.DoesNotExist:
        return Response({'detail': 'Property not found.'}, status=status.HTTP_404_NOT_FOUND)

    user = request.user
    if not (is_admin(user) or prop.owner == user or is_agent_for(user, prop)):
        return Response({'detail': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)

    if request.method == 'GET':
        entries = AdditionalIncome.objects.filter(unit__property=prop).select_related('unit', 'charge_type')
        return Response(AdditionalIncomeSerializer(entries, many=True).data)

    elif request.method == 'POST':
        if not (is_admin(user) or prop.owner == user):
            return Response({'detail': 'Only the property owner can record additional income.'}, status=status.HTTP_403_FORBIDDEN)
        serializer = AdditionalIncomeSerializer(data=request.data)
        if serializer.is_valid():
            unit = serializer.validated_data['unit']
            charge_type = serializer.validated_data['charge_type']
            if unit.property_id != prop.id:
                return Response({'detail': 'Unit does not belong to this property.'}, status=status.HTTP_400_BAD_REQUEST)
            if charge_type.property_id != prop.id:
                return Response({'detail': 'Charge type does not belong to this property.'}, status=status.HTTP_400_BAD_REQUEST)
            serializer.save(recorded_by=user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(methods=['GET'], summary="Get additional income entry detail")
@extend_schema(
    methods=['PUT'],
    summary="Update an additional income entry",
    examples=[OpenApiExample("Update amount", request_only=True, value={"amount": "1750.00"})],
)
@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def additional_income_detail(request, property_pk, pk):
    try:
        prop = Property.objects.get(pk=property_pk)
    except Property.DoesNotExist:
        return Response({'detail': 'Property not found.'}, status=status.HTTP_404_NOT_FOUND)

    try:
        entry = AdditionalIncome.objects.select_related('unit', 'charge_type').get(pk=pk, unit__property=prop)
    except AdditionalIncome.DoesNotExist:
        return Response({'detail': 'Entry not found.'}, status=status.HTTP_404_NOT_FOUND)

    user = request.user
    if not (is_admin(user) or prop.owner == user or is_agent_for(user, prop)):
        return Response({'detail': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)

    if request.method == 'GET':
        return Response(AdditionalIncomeSerializer(entry).data)

    if not (is_admin(user) or prop.owner == user):
        return Response({'detail': 'Only the property owner can modify income entries.'}, status=status.HTTP_403_FORBIDDEN)

    if request.method == 'PUT':
        serializer = AdditionalIncomeSerializer(entry, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'DELETE':
        entry.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ── Expenses ────────────────────────────────────────────────────────────────────

@extend_schema(methods=['GET'], summary="List expenses for a property")
@extend_schema(
    methods=['POST'],
    summary="Record an expense for a property",
    examples=[
        OpenApiExample("Insurance premium", request_only=True, value={
            "property": 1,
            "category": "insurance",
            "amount": "15000.00",
            "date": "2024-03-01",
            "description": "Annual building insurance premium",
        }),
        OpenApiExample("Utility — water bill", request_only=True, value={
            "property": 1,
            "unit": 2,
            "category": "utility",
            "amount": "3200.00",
            "date": "2024-03-05",
            "description": "Water bill March",
        }),
    ],
)
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def expense_list_create(request, property_pk):
    try:
        prop = Property.objects.get(pk=property_pk)
    except Property.DoesNotExist:
        return Response({'detail': 'Property not found.'}, status=status.HTTP_404_NOT_FOUND)

    user = request.user
    if not (is_admin(user) or prop.owner == user or is_agent_for(user, prop)):
        return Response({'detail': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)

    if request.method == 'GET':
        expenses = Expense.objects.filter(property=prop).select_related('unit', 'maintenance_request')
        return Response(ExpenseSerializer(expenses, many=True).data)

    elif request.method == 'POST':
        if not (is_admin(user) or prop.owner == user):
            return Response({'detail': 'Only the property owner can record expenses.'}, status=status.HTTP_403_FORBIDDEN)
        serializer = ExpenseSerializer(data=request.data)
        if serializer.is_valid():
            unit = serializer.validated_data.get('unit')
            if unit and unit.property_id != prop.id:
                return Response({'detail': 'Unit does not belong to this property.'}, status=status.HTTP_400_BAD_REQUEST)
            serializer.save(property=prop, recorded_by=user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(methods=['GET'], summary="Get expense detail")
@extend_schema(
    methods=['PUT'],
    summary="Update an expense",
    examples=[OpenApiExample("Correct amount", request_only=True, value={"amount": "16500.00"})],
)
@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def expense_detail(request, property_pk, pk):
    try:
        prop = Property.objects.get(pk=property_pk)
    except Property.DoesNotExist:
        return Response({'detail': 'Property not found.'}, status=status.HTTP_404_NOT_FOUND)

    try:
        expense = Expense.objects.get(pk=pk, property=prop)
    except Expense.DoesNotExist:
        return Response({'detail': 'Expense not found.'}, status=status.HTTP_404_NOT_FOUND)

    user = request.user
    if not (is_admin(user) or prop.owner == user or is_agent_for(user, prop)):
        return Response({'detail': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)

    if request.method == 'GET':
        return Response(ExpenseSerializer(expense).data)

    if not (is_admin(user) or prop.owner == user):
        return Response({'detail': 'Only the property owner can modify expenses.'}, status=status.HTTP_403_FORBIDDEN)

    if request.method == 'PUT':
        serializer = ExpenseSerializer(expense, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'DELETE':
        expense.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ── Billing preview ─────────────────────────────────────────────────────────────

@extend_schema(
    methods=['GET'],
    summary="Preview next invoice generation date and rent roll for a property",
    examples=[
        OpenApiExample(
            "Preview",
            value={
                'configured': True,
                'property': 1,
                'invoice_lead_days': 2,
                'rent_due_day': 5,
                'grace_period_days': 3,
                'next_invoice_generation_date': '2026-04-03',
                'next_rent_due_date': '2026-04-08',
                'active_lease_count': 4,
                'estimated_monthly_rent_total': '180000.00',
            },
        ),
    ],
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def billing_preview(request, property_pk):
    try:
        prop = Property.objects.get(pk=property_pk)
    except Property.DoesNotExist:
        return Response({'detail': 'Property not found.'}, status=status.HTTP_404_NOT_FOUND)

    user = request.user
    if not (is_admin(user) or prop.owner == user or is_agent_for(user, prop)):
        return Response({'detail': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)

    today = timezone.now().date()
    active = Lease.objects.filter(unit__property=prop, is_active=True)
    lease_count = active.count()
    rent_total = active.aggregate(t=Sum('rent_amount'))['t'] or Decimal('0')

    try:
        config = prop.billing_config
    except BillingConfig.DoesNotExist:
        return Response({
            'configured': False,
            'property': prop.id,
            'invoice_lead_days': 0,
            'rent_due_day': 1,
            'grace_period_days': 0,
            'next_invoice_generation_date': None,
            'next_rent_due_date': None,
            'active_lease_count': lease_count,
            'estimated_monthly_rent_total': str(rent_total),
        })

    next_gen = _next_invoice_generation_on_or_after(today, config.rent_due_day, config.invoice_lead_days)
    next_due = None
    if next_gen:
        anchor = _next_rent_anchor_from_gen(next_gen, config.rent_due_day)
        next_due = anchor + timedelta(days=config.grace_period_days)

    return Response({
        'configured': True,
        'property': prop.id,
        'invoice_lead_days': config.invoice_lead_days,
        'rent_due_day': config.rent_due_day,
        'grace_period_days': config.grace_period_days,
        'next_invoice_generation_date': next_gen,
        'next_rent_due_date': next_due,
        'active_lease_count': lease_count,
        'estimated_monthly_rent_total': str(rent_total),
    })


# ── Financial Report ────────────────────────────────────────────────────────────

@extend_schema(
    methods=['GET'],
    summary="Financial report for a property",
    examples=[
        OpenApiExample("Monthly report", value={
            "property": 1,
            "period": "2024-03",
            "income": {
                "rent_invoiced": "135000.00",
                "late_fees_invoiced": "6750.00",
                "total_invoiced": "141750.00",
                "total_collected": "135000.00",
                "additional_income": "4500.00",
                "additional_income_by_type": {"Water": "1500.00", "Electricity": "3000.00"},
                "total_income": "139500.00",
            },
            "expenses": {
                "total": "22000.00",
                "by_category": {"maintenance": "12000.00", "utility": "7000.00", "insurance": "3000.00"},
            },
            "net_income": "117500.00",
            "invoices": {"paid": 3, "pending": 0, "overdue": 0, "partial": 0, "cancelled": 0},
            "occupancy": {
                "occupied_units": 8,
                "total_units": 10,
                "occupancy_pct": "80.00",
            },
            "occupancy_series": [
                {
                    "period": "2024-03",
                    "occupied_units": 8,
                    "total_units": 10,
                    "occupancy_pct": "80.00",
                },
            ],
            "occupancy_avg_pct": "80.00",
        }),
    ],
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def financial_report(request, property_pk):
    try:
        prop = Property.objects.get(pk=property_pk)
    except Property.DoesNotExist:
        return Response({'detail': 'Property not found.'}, status=status.HTTP_404_NOT_FOUND)

    user = request.user
    if not (is_admin(user) or prop.owner == user or is_agent_for(user, prop)):
        return Response({'detail': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)

    year_param = request.query_params.get('year')
    month_param = request.query_params.get('month')

    if not year_param:
        return Response({'detail': 'year query parameter is required.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        year = int(year_param)
    except ValueError:
        return Response({'detail': 'year must be an integer.'}, status=status.HTTP_400_BAD_REQUEST)

    month = None
    if month_param:
        try:
            month = int(month_param)
            if not (1 <= month <= 12):
                raise ValueError
        except ValueError:
            return Response({'detail': 'month must be an integer between 1 and 12.'}, status=status.HTTP_400_BAD_REQUEST)

    period_label = f"{year}-{month:02d}" if month else str(year)

    # Build filters
    if month:
        inv_f = {'period_start__year': year, 'period_start__month': month}
        pay_f = {'paid_at__year': year, 'paid_at__month': month}
        ai_f = {'date__year': year, 'date__month': month}
        exp_f = {'date__year': year, 'date__month': month}
    else:
        inv_f = {'period_start__year': year}
        pay_f = {'paid_at__year': year}
        ai_f = {'date__year': year}
        exp_f = {'date__year': year}

    # Invoices for the period
    invoices_qs = Invoice.objects.filter(lease__unit__property=prop, **inv_f)
    rent_invoiced = invoices_qs.aggregate(t=Sum('rent_amount'))['t'] or Decimal('0')
    late_fees_invoiced = invoices_qs.aggregate(t=Sum('late_fee_amount'))['t'] or Decimal('0')
    invoice_counts = {
        item['status']: item['c']
        for item in invoices_qs.values('status').annotate(c=Count('id'))
    }

    # Rent payments received in the period
    total_collected = (
        Payment.objects.filter(status='completed', invoice__lease__unit__property=prop, **pay_f)
        .aggregate(t=Sum('amount'))['t'] or Decimal('0')
    )

    # Additional income
    ai_qs = AdditionalIncome.objects.filter(unit__property=prop, **ai_f)
    additional_total = ai_qs.aggregate(t=Sum('amount'))['t'] or Decimal('0')
    ai_by_type = {
        row['charge_type__name']: str(row['t'])
        for row in ai_qs.values('charge_type__name').annotate(t=Sum('amount'))
    }

    # Expenses
    exp_qs = Expense.objects.filter(property=prop, **exp_f)
    expense_total = exp_qs.aggregate(t=Sum('amount'))['t'] or Decimal('0')
    exp_by_cat = {
        row['category']: str(row['t'])
        for row in exp_qs.values('category').annotate(t=Sum('amount'))
    }

    total_income = total_collected + additional_total
    net_income = total_income - expense_total

    if month:
        p_start = date(year, month, 1)
        p_end = date(year, month, calendar.monthrange(year, month)[1])
        occupancy = _occupancy_for_period(prop, p_start, p_end)
        occupancy_series = [{'period': period_label, **occupancy}]
        occupancy_avg_pct = occupancy['occupancy_pct']
    else:
        occupancy = None
        occupancy_series = []
        month_pcts = []
        for m in range(1, 13):
            p_start = date(year, m, 1)
            p_end = date(year, m, calendar.monthrange(year, m)[1])
            row = _occupancy_for_period(prop, p_start, p_end)
            occupancy_series.append({'period': f'{year}-{m:02d}', **row})
            if row['occupancy_pct'] is not None:
                month_pcts.append(Decimal(row['occupancy_pct']))
        occupancy_avg_pct = None
        if month_pcts:
            occupancy_avg_pct = str(
                (sum(month_pcts) / Decimal(len(month_pcts))).quantize(Decimal('0.01'))
            )

    payload = {
        'property': property_pk,
        'period': period_label,
        'income': {
            'rent_invoiced': str(rent_invoiced),
            'late_fees_invoiced': str(late_fees_invoiced),
            'total_invoiced': str(rent_invoiced + late_fees_invoiced),
            'total_collected': str(total_collected),
            'additional_income': str(additional_total),
            'additional_income_by_type': ai_by_type,
            'total_income': str(total_income),
        },
        'expenses': {
            'total': str(expense_total),
            'by_category': exp_by_cat,
        },
        'net_income': str(net_income),
        'invoices': {
            'paid': invoice_counts.get('paid', 0),
            'pending': invoice_counts.get('pending', 0),
            'overdue': invoice_counts.get('overdue', 0),
            'partial': invoice_counts.get('partial', 0),
            'cancelled': invoice_counts.get('cancelled', 0),
        },
        'occupancy': occupancy,
        'occupancy_series': occupancy_series,
        'occupancy_avg_pct': occupancy_avg_pct,
    }
    return Response(payload)
