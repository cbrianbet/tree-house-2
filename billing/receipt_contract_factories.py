"""Builders for receipt API contract tests (minimal duplication vs billing/tests.py)."""
import uuid
from datetime import date, datetime
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.authtoken.models import Token

from authentication.models import Role
from property.models import Property, Unit, Lease, PropertyAgent
from billing.models import Invoice, Payment, Receipt

User = get_user_model()


def contract_make_user(username: str, role_name: str):
    role = Role.objects.get_or_create(name=role_name)[0]
    user = User.objects.create_user(
        username=username,
        password='contract-pass',
        role=role,
        email=f'{username}@contract.test',
    )
    token = Token.objects.create(user=user)
    return user, token


def contract_property_unit_lease(landlord, tenant, *, property_name='Contract Prop', unit_name='Unit A'):
    prop = Property.objects.create(
        name=property_name,
        property_type='apartment',
        owner=landlord,
        created_by=landlord,
    )
    unit = Unit.objects.create(
        property=prop,
        name=unit_name,
        price='1000',
        created_by=landlord,
    )
    lease = Lease.objects.create(
        unit=unit,
        tenant=tenant,
        start_date=date(2026, 1, 1),
        rent_amount='1000',
        is_active=True,
    )
    return prop, unit, lease


def contract_create_paid_receipt(
    lease: Lease,
    *,
    year: int = 2026,
    period_month: int = 4,
    amount: str = '1000',
    payment_method: str = 'card',
    receipt_number: str | None = None,
    paid_at=None,
    transaction_reference: str = '',
    stripe_intent_id: str | None = None,
):
    inv = Invoice.objects.create(
        lease=lease,
        period_start=date(year, period_month, 1),
        period_end=date(year, period_month, 28),
        due_date=date(year, period_month, 5),
        rent_amount=Decimal(amount),
        late_fee_amount=Decimal('0'),
        total_amount=Decimal(amount),
        status='paid',
    )
    inv.refresh_from_db()
    if paid_at is None:
        paid_at = timezone.make_aware(datetime(year, period_month, 10, 12, 0, 0))
    pay = Payment.objects.create(
        invoice=inv,
        amount=Decimal(amount),
        stripe_payment_intent_id=stripe_intent_id or f'pi_contract_{uuid.uuid4().hex}',
        payment_method=payment_method,
        transaction_reference=transaction_reference or '',
        status='completed',
        paid_at=paid_at,
    )
    rn = receipt_number or f'RCP-CONTRACT-{pay.id}'
    return Receipt.objects.create(payment=pay, receipt_number=rn)


def contract_assign_agent(landlord, agent, prop):
    return PropertyAgent.objects.create(property=prop, agent=agent, appointed_by=landlord)
