import json
import stripe
from django.conf import settings
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema, OpenApiExample

from property.models import Property, Lease
from property.views import is_admin, is_landlord, is_agent_for
from .models import BillingConfig, Invoice, Payment, Receipt
from .serializers import (
    BillingConfigSerializer, InvoiceSerializer,
    PaymentSerializer, ReceiptSerializer,
)
from .utils import generate_receipt_number

stripe.api_key = settings.STRIPE_SECRET_KEY


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

    if not (is_admin(request.user) or property.owner == request.user):
        return Response({'detail': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)

    if request.method == 'GET':
        try:
            config = property.billing_config
            return Response(BillingConfigSerializer(config).data)
        except BillingConfig.DoesNotExist:
            return Response({'detail': 'No billing config set for this property.'}, status=status.HTTP_404_NOT_FOUND)

    elif request.method == 'POST':
        try:
            config = property.billing_config
            serializer = BillingConfigSerializer(config, data=request.data, partial=True)
        except BillingConfig.DoesNotExist:
            serializer = BillingConfigSerializer(data=request.data)

        if serializer.is_valid():
            serializer.save(property=property, updated_by=request.user)
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ── Invoices ───────────────────────────────────────────────────────────────────

@extend_schema(methods=['GET'], summary="List invoices")
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def invoice_list(request):
    user = request.user
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
        stripe_payment_intent_id=intent['id'],
    )

    return Response({'client_secret': intent['client_secret']}, status=status.HTTP_201_CREATED)


@extend_schema(methods=['GET'], summary="List payments for an invoice")
@api_view(['GET'])
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

    payments = invoice.payments.all()
    return Response(PaymentSerializer(payments, many=True).data)


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
        Receipt.objects.create(
            payment=payment,
            receipt_number=generate_receipt_number(),
        )


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
