import calendar
from datetime import date, datetime, timedelta
from decimal import Decimal
from unittest.mock import patch, MagicMock

from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework.authtoken.models import Token
from rest_framework import status
from django.contrib.auth import get_user_model

from authentication.models import Role
from property.models import Property, Unit, Lease, PropertyAgent
from billing.models import (
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
from billing.utils import generate_receipt_number, generate_invoice_number
from billing.serializers import ReceiptSerializer
from billing.views import _receipt_base_queryset
from billing.pagination import ReceiptListPagination

User = get_user_model()


def make_user(username, role_name, is_staff=False):
    role = Role.objects.get_or_create(name=role_name)[0]
    user = User.objects.create_user(username=username, password='testpass', role=role, email=f'{username}@test.com')
    if is_staff:
        user.is_staff = True
        user.save()
    token = Token.objects.create(user=user)
    return user, token


def make_property(owner):
    return Property.objects.create(name='Test Property', property_type='apartment', owner=owner, created_by=owner)


def make_unit(prop, owner):
    return Unit.objects.create(property=prop, name='Unit 1', price='45000', created_by=owner)


def make_lease(unit, tenant):
    return Lease.objects.create(unit=unit, tenant=tenant, start_date=date.today(), rent_amount='45000', is_active=True)


def make_invoice(lease, due_days=5, status='pending'):
    today = date.today()
    return Invoice.objects.create(
        lease=lease,
        period_start=today.replace(day=1),
        period_end=today.replace(day=28),
        due_date=today + timedelta(days=due_days),
        rent_amount=Decimal('45000'),
        late_fee_amount=Decimal('0'),
        total_amount=Decimal('45000'),
        status=status,
    )


class BillingConfigTests(APITestCase):
    def setUp(self):
        self.landlord, self.landlord_token = make_user('landlord1', 'Landlord')
        self.other_landlord, self.other_token = make_user('landlord2', 'Landlord')
        self.tenant, self.tenant_token = make_user('tenant1', 'Tenant')
        self.prop = make_property(self.landlord)

    def auth(self, token):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

    def test_landlord_can_set_billing_config(self):
        self.auth(self.landlord_token)
        data = {
            'rent_due_day': 5,
            'grace_period_days': 3,
            'late_fee_percentage': '5.00',
        }
        response = self.client.post(reverse('billing-config', args=[self.prop.id]), data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(BillingConfig.objects.filter(property=self.prop).count(), 1)

    def test_landlord_can_update_billing_config(self):
        BillingConfig.objects.create(
            property=self.prop, rent_due_day=5, grace_period_days=0,
            late_fee_percentage='5.00', updated_by=self.landlord
        )
        self.auth(self.landlord_token)
        response = self.client.post(reverse('billing-config', args=[self.prop.id]), {'grace_period_days': 7})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['grace_period_days'], 7)

    def test_invalid_due_day_rejected(self):
        self.auth(self.landlord_token)
        data = {'rent_due_day': 31, 'grace_period_days': 0, 'late_fee_percentage': '5.00'}
        response = self.client.post(reverse('billing-config', args=[self.prop.id]), data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_other_landlord_cannot_set_config(self):
        self.auth(self.other_token)
        data = {'rent_due_day': 5, 'grace_period_days': 0, 'late_fee_percentage': '5.00'}
        response = self.client.post(reverse('billing-config', args=[self.prop.id]), data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_tenant_cannot_set_config(self):
        self.auth(self.tenant_token)
        data = {'rent_due_day': 5, 'grace_period_days': 0, 'late_fee_percentage': '5.00'}
        response = self.client.post(reverse('billing-config', args=[self.prop.id]), data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_get_config_returns_defaults_when_unset(self):
        self.auth(self.landlord_token)
        response = self.client.get(reverse('billing-config', args=[self.prop.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['configured'])
        self.assertEqual(response.data['rent_due_day'], 1)
        self.assertEqual(response.data['invoice_lead_days'], 0)

    def test_assigned_agent_can_get_billing_config(self):
        from property.models import PropertyAgent
        agent, agent_token = make_user('agent_bc', 'Agent')
        PropertyAgent.objects.create(property=self.prop, agent=agent, appointed_by=self.landlord)
        self.auth(agent_token)
        response = self.client.get(reverse('billing-config', args=[self.prop.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_agent_cannot_post_billing_config(self):
        agent, agent_token = make_user('agent_bc2', 'Agent')
        from property.models import PropertyAgent
        PropertyAgent.objects.create(property=self.prop, agent=agent, appointed_by=self.landlord)
        self.auth(agent_token)
        response = self.client.post(
            reverse('billing-config', args=[self.prop.id]),
            {'rent_due_day': 5, 'grace_period_days': 0, 'late_fee_percentage': '5.00'},
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_late_fee_fixed_mode_requires_amount(self):
        self.auth(self.landlord_token)
        response = self.client.post(
            reverse('billing-config', args=[self.prop.id]),
            {
                'rent_due_day': 5,
                'grace_period_days': 0,
                'late_fee_percentage': '5.00',
                'late_fee_mode': 'fixed',
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invoice_lead_days_above_27_rejected(self):
        self.auth(self.landlord_token)
        response = self.client.post(
            reverse('billing-config', args=[self.prop.id]),
            {
                'rent_due_day': 5,
                'grace_period_days': 0,
                'late_fee_percentage': '5.00',
                'invoice_lead_days': 28,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class InvoiceTests(APITestCase):
    def setUp(self):
        self.landlord, self.landlord_token = make_user('landlord1', 'Landlord')
        self.tenant, self.tenant_token = make_user('tenant1', 'Tenant')
        self.other_tenant, self.other_token = make_user('tenant2', 'Tenant')
        self.agent, self.agent_token = make_user('agent1', 'Agent')

        self.prop = make_property(self.landlord)
        self.unit = make_unit(self.prop, self.landlord)
        self.lease = make_lease(self.unit, self.tenant)
        self.invoice = make_invoice(self.lease)

    def auth(self, token):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

    def test_tenant_sees_own_invoices(self):
        self.auth(self.tenant_token)
        response = self.client.get(reverse('invoice-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_other_tenant_sees_no_invoices(self):
        self.auth(self.other_token)
        response = self.client.get(reverse('invoice-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

    def test_landlord_sees_property_invoices(self):
        self.auth(self.landlord_token)
        response = self.client.get(reverse('invoice-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_assigned_agent_sees_invoices(self):
        PropertyAgent.objects.create(property=self.prop, agent=self.agent, appointed_by=self.landlord)
        self.auth(self.agent_token)
        response = self.client.get(reverse('invoice-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_unassigned_agent_sees_no_invoices(self):
        self.auth(self.agent_token)
        response = self.client.get(reverse('invoice-list'))
        self.assertEqual(len(response.data), 0)

    def test_tenant_can_retrieve_own_invoice(self):
        self.auth(self.tenant_token)
        response = self.client.get(reverse('invoice-detail', args=[self.invoice.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'pending')

    def test_other_tenant_cannot_retrieve_invoice(self):
        self.auth(self.other_token)
        response = self.client.get(reverse('invoice-detail', args=[self.invoice.id]))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class InvoiceCreateTests(APITestCase):
    def setUp(self):
        self.landlord, self.landlord_token = make_user('landlord_ic', 'Landlord')
        self.other_landlord, self.other_token = make_user('landlord_ic2', 'Landlord')
        self.tenant, self.tenant_token = make_user('tenant_ic', 'Tenant')
        self.agent, self.agent_token = make_user('agent_ic', 'Agent')
        self.admin, self.admin_token = make_user('admin_ic', 'Admin', is_staff=True)

        self.prop = make_property(self.landlord)
        self.unit = make_unit(self.prop, self.landlord)
        self.lease = make_lease(self.unit, self.tenant)
        BillingConfig.objects.create(
            property=self.prop,
            rent_due_day=5,
            grace_period_days=3,
            late_fee_percentage='5.00',
            updated_by=self.landlord,
        )

    def auth(self, token):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

    def _next_month_period(self):
        today = date.today()
        if today.month == 12:
            y, m = today.year + 1, 1
        else:
            y, m = today.year, today.month + 1
        ps = date(y, m, 1)
        pe = date(y, m, calendar.monthrange(y, m)[1])
        return ps, pe

    def _create_payload(self, lease_id=None, **overrides):
        ps, pe = self._next_month_period()
        payload = {
            'lease': lease_id if lease_id is not None else self.lease.id,
            'period_start': ps.isoformat(),
            'period_end': pe.isoformat(),
            'due_date': ps.isoformat(),
        }
        payload.update(overrides)
        return payload

    def test_landlord_can_create_invoice(self):
        self.auth(self.landlord_token)
        response = self.client.post(reverse('invoice-list'), self._create_payload())
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Decimal(response.data['rent_amount']), Decimal('45000'))
        self.assertEqual(Decimal(response.data['late_fee_amount']), Decimal('0'))
        self.assertEqual(Decimal(response.data['total_amount']), Decimal('45000'))
        self.assertEqual(response.data['status'], 'pending')

    def test_rent_amount_override(self):
        self.auth(self.landlord_token)
        response = self.client.post(
            reverse('invoice-list'),
            self._create_payload(rent_amount='40000.00'),
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Decimal(response.data['rent_amount']), Decimal('40000'))
        self.assertEqual(Decimal(response.data['total_amount']), Decimal('40000'))

    def test_admin_can_create_invoice(self):
        self.auth(self.admin_token)
        response = self.client.post(reverse('invoice-list'), self._create_payload())
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_assigned_agent_can_create_invoice(self):
        PropertyAgent.objects.create(
            property=self.prop, agent=self.agent, appointed_by=self.landlord
        )
        self.auth(self.agent_token)
        response = self.client.post(reverse('invoice-list'), self._create_payload())
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_unassigned_agent_forbidden(self):
        self.auth(self.agent_token)
        response = self.client.post(reverse('invoice-list'), self._create_payload())
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_other_landlord_forbidden(self):
        self.auth(self.other_token)
        response = self.client.post(reverse('invoice-list'), self._create_payload())
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_tenant_forbidden(self):
        self.auth(self.tenant_token)
        response = self.client.post(reverse('invoice-list'), self._create_payload())
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_duplicate_lease_period_returns_400(self):
        self.auth(self.landlord_token)
        payload = self._create_payload()
        r1 = self.client.post(reverse('invoice-list'), payload)
        self.assertEqual(r1.status_code, status.HTTP_201_CREATED)
        r2 = self.client.post(reverse('invoice-list'), payload)
        self.assertEqual(r2.status_code, status.HTTP_400_BAD_REQUEST)

    def test_missing_billing_config_returns_400(self):
        prop2 = make_property(self.landlord)
        unit2 = make_unit(prop2, self.landlord)
        lease2 = make_lease(unit2, self.tenant)
        self.auth(self.landlord_token)
        response = self.client.post(reverse('invoice-list'), self._create_payload(lease_id=lease2.id))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_inactive_lease_returns_400(self):
        self.lease.is_active = False
        self.lease.save()
        self.auth(self.landlord_token)
        response = self.client.post(reverse('invoice-list'), self._create_payload())
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_period_outside_lease_returns_400(self):
        end = date.today()
        self.lease.end_date = end
        self.lease.save()
        self.auth(self.landlord_token)
        future_start = end + timedelta(days=40)
        future_end = future_start + timedelta(days=27)
        response = self.client.post(
            reverse('invoice-list'),
            {
                'lease': self.lease.id,
                'period_start': future_start.isoformat(),
                'period_end': future_end.isoformat(),
                'due_date': future_start.isoformat(),
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class PaymentTests(APITestCase):
    def setUp(self):
        self.landlord, self.landlord_token = make_user('landlord1', 'Landlord')
        self.tenant, self.tenant_token = make_user('tenant1', 'Tenant')
        self.other_tenant, self.other_token = make_user('tenant2', 'Tenant')

        self.prop = make_property(self.landlord)
        self.unit = make_unit(self.prop, self.landlord)
        self.lease = make_lease(self.unit, self.tenant)
        self.invoice = make_invoice(self.lease)

    def auth(self, token):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

    @patch('billing.views.stripe.PaymentIntent.create')
    def test_tenant_can_initiate_payment(self, mock_create):
        mock_create.return_value = MagicMock(id='pi_test123', client_secret='secret_test')
        self.auth(self.tenant_token)
        response = self.client.post(
            reverse('invoice-pay', args=[self.invoice.id]),
            {'amount': '45000.00'}
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('client_secret', response.data)
        self.assertTrue(Payment.objects.filter(invoice=self.invoice).exists())

    def test_other_tenant_cannot_pay_invoice(self):
        self.auth(self.other_token)
        response = self.client.post(
            reverse('invoice-pay', args=[self.invoice.id]),
            {'amount': '45000.00'}
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @patch('billing.views.stripe.PaymentIntent.create')
    def test_cannot_pay_already_paid_invoice(self, mock_create):
        self.invoice.status = 'paid'
        self.invoice.save()
        self.auth(self.tenant_token)
        response = self.client.post(
            reverse('invoice-pay', args=[self.invoice.id]),
            {'amount': '45000.00'}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_amount_required(self):
        self.auth(self.tenant_token)
        response = self.client.post(reverse('invoice-pay', args=[self.invoice.id]), {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_tenant_cannot_record_manual_payment(self):
        self.auth(self.tenant_token)
        response = self.client.post(
            reverse('invoice-payments', args=[self.invoice.id]),
            {'amount': '45000.00'},
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class ManualPaymentRecordTests(APITestCase):
    def setUp(self):
        self.landlord, self.landlord_token = make_user('landlord_mp', 'Landlord')
        self.other_landlord, self.other_token = make_user('landlord_mp2', 'Landlord')
        self.tenant, self.tenant_token = make_user('tenant_mp', 'Tenant')
        self.agent, self.agent_token = make_user('agent_mp', 'Agent')
        self.admin, self.admin_token = make_user('admin_mp', 'Admin', is_staff=True)

        self.prop = make_property(self.landlord)
        self.unit = make_unit(self.prop, self.landlord)
        self.lease = make_lease(self.unit, self.tenant)
        self.invoice = make_invoice(self.lease)

    def auth(self, token):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

    @patch('notifications.utils.create_notification')
    def test_landlord_records_full_payment(self, mock_notify):
        self.auth(self.landlord_token)
        response = self.client.post(
            reverse('invoice-payments', args=[self.invoice.id]),
            {'amount': '45000.00'},
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['payment']['stripe_payment_intent_id'].startswith('manual-'))
        self.assertEqual(response.data['payment']['status'], 'completed')
        self.assertIn('receipt_number', response.data['receipt'])
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.status, 'paid')
        self.assertTrue(Receipt.objects.filter(payment_id=response.data['payment']['id']).exists())
        mock_notify.assert_called_once()

    @patch('notifications.utils.create_notification')
    def test_manual_payment_skips_notification_when_disabled(self, mock_notify):
        PropertyBillingNotificationSettings.objects.create(
            property=self.prop,
            send_receipt_on_payment=False,
        )
        self.auth(self.landlord_token)
        response = self.client.post(
            reverse('invoice-payments', args=[self.invoice.id]),
            {'amount': '45000.00'},
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        mock_notify.assert_not_called()

    def test_landlord_partial_then_full(self):
        self.auth(self.landlord_token)
        r1 = self.client.post(
            reverse('invoice-payments', args=[self.invoice.id]),
            {'amount': '20000.00'},
        )
        self.assertEqual(r1.status_code, status.HTTP_201_CREATED)
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.status, 'partial')
        r2 = self.client.post(
            reverse('invoice-payments', args=[self.invoice.id]),
            {'amount': '25000.00'},
        )
        self.assertEqual(r2.status_code, status.HTTP_201_CREATED)
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.status, 'paid')

    def test_amount_exceeds_remaining_returns_400(self):
        self.auth(self.landlord_token)
        response = self.client.post(
            reverse('invoice-payments', args=[self.invoice.id]),
            {'amount': '50000.00'},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_fully_paid_cannot_record_more(self):
        self.auth(self.landlord_token)
        self.client.post(
            reverse('invoice-payments', args=[self.invoice.id]),
            {'amount': '45000.00'},
        )
        response = self.client.post(
            reverse('invoice-payments', args=[self.invoice.id]),
            {'amount': '1.00'},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cancelled_invoice_rejected(self):
        self.invoice.status = 'cancelled'
        self.invoice.save()
        self.auth(self.landlord_token)
        response = self.client.post(
            reverse('invoice-payments', args=[self.invoice.id]),
            {'amount': '45000.00'},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_assigned_agent_can_record(self):
        PropertyAgent.objects.create(
            property=self.prop, agent=self.agent, appointed_by=self.landlord
        )
        self.auth(self.agent_token)
        response = self.client.post(
            reverse('invoice-payments', args=[self.invoice.id]),
            {'amount': '45000.00'},
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_unassigned_agent_forbidden(self):
        self.auth(self.agent_token)
        response = self.client.post(
            reverse('invoice-payments', args=[self.invoice.id]),
            {'amount': '45000.00'},
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_other_landlord_forbidden(self):
        self.auth(self.other_token)
        response = self.client.post(
            reverse('invoice-payments', args=[self.invoice.id]),
            {'amount': '45000.00'},
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_record(self):
        self.auth(self.admin_token)
        response = self.client.post(
            reverse('invoice-payments', args=[self.invoice.id]),
            {'amount': '45000.00'},
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)


class ReceiptTests(APITestCase):
    def setUp(self):
        self.landlord, self.landlord_token = make_user('landlord1', 'Landlord')
        self.tenant, self.tenant_token = make_user('tenant1', 'Tenant')

        self.prop = make_property(self.landlord)
        self.unit = make_unit(self.prop, self.landlord)
        self.lease = make_lease(self.unit, self.tenant)
        self.invoice = make_invoice(self.lease, status='paid')

        self.payment = Payment.objects.create(
            invoice=self.invoice,
            amount=Decimal('45000'),
            stripe_payment_intent_id='pi_test_receipt',
            status='completed',
            paid_at=timezone.now(),
        )
        self.receipt = Receipt.objects.create(
            payment=self.payment,
            receipt_number='RCP-202603-0001',
        )

    def auth(self, token):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

    def test_tenant_can_list_receipts(self):
        self.auth(self.tenant_token)
        response = self.client.get(reverse('receipt-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data['results']), 1)

    def test_tenant_can_retrieve_receipt(self):
        self.auth(self.tenant_token)
        response = self.client.get(reverse('receipt-detail', args=[self.receipt.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['receipt_number'], 'RCP-202603-0001')

    def test_landlord_can_list_receipts(self):
        self.auth(self.landlord_token)
        response = self.client.get(reverse('receipt-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(len(response.data['results']), 1)


class ReceiptNumberTests(APITestCase):
    def test_receipt_number_format(self):
        number = generate_receipt_number()
        self.assertRegex(number, r'^RCP-\d{6}-\d{4}$')

    def test_receipt_number_increments(self):
        landlord, _ = make_user('landlord_rn', 'Landlord')
        tenant, _ = make_user('tenant_rn', 'Tenant')
        prop = make_property(landlord)
        unit = make_unit(prop, landlord)
        lease = make_lease(unit, tenant)
        invoice = make_invoice(lease)

        payment = Payment.objects.create(
            invoice=invoice, amount=Decimal('45000'),
            stripe_payment_intent_id='pi_seq_1', status='completed', paid_at=timezone.now(),
        )
        r1 = Receipt.objects.create(payment=payment, receipt_number=generate_receipt_number())

        invoice2 = make_invoice(Lease.objects.create(
            unit=make_unit(prop, landlord), tenant=tenant,
            start_date=date.today(), rent_amount='45000', is_active=True,
        ))
        payment2 = Payment.objects.create(
            invoice=invoice2, amount=Decimal('45000'),
            stripe_payment_intent_id='pi_seq_2', status='completed', paid_at=timezone.now(),
        )
        r2 = Receipt.objects.create(payment=payment2, receipt_number=generate_receipt_number())

        seq1 = int(r1.receipt_number.split('-')[-1])
        seq2 = int(r2.receipt_number.split('-')[-1])
        self.assertEqual(seq2, seq1 + 1)


class ProcessBillingCommandTests(APITestCase):
    def setUp(self):
        self.landlord, _ = make_user('landlord_cmd', 'Landlord')
        self.tenant, _ = make_user('tenant_cmd', 'Tenant')
        self.prop = make_property(self.landlord)
        self.unit = make_unit(self.prop, self.landlord)
        self.lease = make_lease(self.unit, self.tenant)

        today = date.today()
        BillingConfig.objects.create(
            property=self.prop,
            rent_due_day=today.day,
            grace_period_days=3,
            late_fee_percentage=Decimal('5.00'),
            updated_by=self.landlord,
        )

    def test_invoice_generated_on_due_day(self):
        from django.core.management import call_command
        call_command('process_billing', verbosity=0)
        self.assertEqual(Invoice.objects.filter(lease=self.lease).count(), 1)

    def test_invoice_not_duplicated(self):
        from django.core.management import call_command
        call_command('process_billing', verbosity=0)
        call_command('process_billing', verbosity=0)
        self.assertEqual(Invoice.objects.filter(lease=self.lease).count(), 1)

    def test_late_fee_applied_to_overdue_invoice(self):
        from django.core.management import call_command
        overdue_invoice = Invoice.objects.create(
            lease=self.lease,
            period_start=date.today().replace(day=1),
            period_end=date.today(),
            due_date=date.today() - timedelta(days=1),
            rent_amount=Decimal('45000'),
            late_fee_amount=Decimal('0'),
            total_amount=Decimal('45000'),
            status='pending',
        )
        call_command('process_billing', verbosity=0)
        overdue_invoice.refresh_from_db()
        self.assertEqual(overdue_invoice.status, 'overdue')
        self.assertEqual(overdue_invoice.late_fee_amount, Decimal('2250.00'))  # 5% of 45000
        self.assertEqual(overdue_invoice.total_amount, Decimal('47250.00'))

    @patch('notifications.utils.create_notification')
    def test_pre_due_reminder_sent(self, mock_notify):
        invoice = Invoice.objects.create(
            lease=self.lease,
            period_start=date.today().replace(day=1),
            period_end=date.today(),
            due_date=date.today() + timedelta(days=3),
            rent_amount=Decimal('45000'),
            late_fee_amount=Decimal('0'),
            total_amount=Decimal('45000'),
            status='pending',
        )
        from django.core.management import call_command
        call_command('process_billing', verbosity=0)
        mock_notify.assert_called()
        self.assertTrue(ReminderLog.objects.filter(invoice=invoice, reminder_type='pre_due').exists())

    @patch('notifications.utils.create_notification')
    def test_reminder_not_sent_twice(self, mock_notify):
        invoice = Invoice.objects.create(
            lease=self.lease,
            period_start=date.today().replace(day=1),
            period_end=date.today(),
            due_date=date.today() + timedelta(days=3),
            rent_amount=Decimal('45000'),
            late_fee_amount=Decimal('0'),
            total_amount=Decimal('45000'),
            status='pending',
        )
        ReminderLog.objects.create(invoice=invoice, reminder_type='pre_due')
        from django.core.management import call_command
        call_command('process_billing', verbosity=0)
        mock_notify.assert_not_called()

    @patch('notifications.utils.create_notification')
    def test_pre_due_disabled_when_notification_settings_null(self, mock_notify):
        PropertyBillingNotificationSettings.objects.create(
            property=self.prop,
            remind_before_due_days=None,
        )
        Invoice.objects.create(
            lease=self.lease,
            period_start=date.today().replace(day=1),
            period_end=date.today(),
            due_date=date.today() + timedelta(days=3),
            rent_amount=Decimal('45000'),
            late_fee_amount=Decimal('0'),
            total_amount=Decimal('45000'),
            status='pending',
        )
        from django.core.management import call_command
        call_command('process_billing', verbosity=0)
        mock_notify.assert_not_called()

    @patch('django.utils.timezone.now')
    def test_invoice_generated_with_lead_days(self, mock_now):
        from django.core.management import call_command
        from django.utils import timezone as dj_tz
        from datetime import datetime

        mock_now.return_value = dj_tz.make_aware(datetime(2026, 4, 13, 12, 0, 0))
        cfg = BillingConfig.objects.get(property=self.prop)
        cfg.rent_due_day = 15
        cfg.invoice_lead_days = 2
        cfg.save()
        call_command('process_billing', verbosity=0)
        inv = Invoice.objects.filter(lease=self.lease).first()
        self.assertIsNotNone(inv)
        self.assertEqual(inv.period_start, date(2026, 4, 1))
        self.assertEqual(inv.due_date, date(2026, 4, 18))

    def test_late_fee_fixed_mode(self):
        from django.core.management import call_command
        cfg = BillingConfig.objects.get(property=self.prop)
        cfg.late_fee_mode = BillingConfig.LATE_FEE_MODE_FIXED
        cfg.late_fee_fixed_amount = Decimal('500.00')
        cfg.save()
        overdue_invoice = Invoice.objects.create(
            lease=self.lease,
            period_start=date.today().replace(day=1),
            period_end=date.today(),
            due_date=date.today() - timedelta(days=1),
            rent_amount=Decimal('45000'),
            late_fee_amount=Decimal('0'),
            total_amount=Decimal('45000'),
            status='pending',
        )
        call_command('process_billing', verbosity=0)
        overdue_invoice.refresh_from_db()
        self.assertEqual(overdue_invoice.late_fee_amount, Decimal('500.00'))
        self.assertEqual(overdue_invoice.total_amount, Decimal('45500.00'))


class ChargeTypeTests(APITestCase):
    def setUp(self):
        self.landlord, self.landlord_token = make_user('landlord1', 'Landlord')
        self.other_landlord, self.other_token = make_user('landlord2', 'Landlord')
        self.agent, self.agent_token = make_user('agent1', 'Agent')
        self.tenant, self.tenant_token = make_user('tenant1', 'Tenant')
        self.prop = make_property(self.landlord)

    def auth(self, token):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

    def test_landlord_can_create_charge_type(self):
        self.auth(self.landlord_token)
        response = self.client.post(
            reverse('charge-type-list', args=[self.prop.id]),
            {'name': 'Water'}
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'Water')

    def test_duplicate_name_rejected(self):
        ChargeType.objects.create(property=self.prop, name='Water', created_by=self.landlord)
        self.auth(self.landlord_token)
        response = self.client.post(
            reverse('charge-type-list', args=[self.prop.id]),
            {'name': 'Water'}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_landlord_can_list_charge_types(self):
        ChargeType.objects.create(property=self.prop, name='Water', created_by=self.landlord)
        ChargeType.objects.create(property=self.prop, name='Electricity', created_by=self.landlord)
        self.auth(self.landlord_token)
        response = self.client.get(reverse('charge-type-list', args=[self.prop.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_assigned_agent_can_list_charge_types(self):
        from property.models import PropertyAgent
        PropertyAgent.objects.create(property=self.prop, agent=self.agent, appointed_by=self.landlord)
        self.auth(self.agent_token)
        response = self.client.get(reverse('charge-type-list', args=[self.prop.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_agent_cannot_create_charge_type(self):
        from property.models import PropertyAgent
        PropertyAgent.objects.create(property=self.prop, agent=self.agent, appointed_by=self.landlord)
        self.auth(self.agent_token)
        response = self.client.post(
            reverse('charge-type-list', args=[self.prop.id]),
            {'name': 'Parking'}
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_other_landlord_cannot_access(self):
        self.auth(self.other_token)
        response = self.client.get(reverse('charge-type-list', args=[self.prop.id]))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_landlord_can_delete_charge_type(self):
        ct = ChargeType.objects.create(property=self.prop, name='Garbage', created_by=self.landlord)
        self.auth(self.landlord_token)
        response = self.client.delete(reverse('charge-type-detail', args=[self.prop.id, ct.id]))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_cannot_delete_charge_type_with_income_entries(self):
        ct = ChargeType.objects.create(property=self.prop, name='Garbage', created_by=self.landlord)
        unit = make_unit(self.prop, self.landlord)
        AdditionalIncome.objects.create(
            unit=unit, charge_type=ct, amount=Decimal('100'), date=date.today(), recorded_by=self.landlord
        )
        self.auth(self.landlord_token)
        response = self.client.delete(reverse('charge-type-detail', args=[self.prop.id, ct.id]))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_inactive_charge_types_hidden_by_default(self):
        ChargeType.objects.create(
            property=self.prop, name='Old', created_by=self.landlord, is_active=False
        )
        ChargeType.objects.create(property=self.prop, name='New', created_by=self.landlord, is_active=True)
        self.auth(self.landlord_token)
        response = self.client.get(reverse('charge-type-list', args=[self.prop.id]))
        self.assertEqual(len(response.data), 1)
        response_all = self.client.get(
            reverse('charge-type-list', args=[self.prop.id]) + '?include_inactive=1'
        )
        self.assertEqual(len(response_all.data), 2)


class BillingPreviewTests(APITestCase):
    def setUp(self):
        self.landlord, self.landlord_token = make_user('landlord_pv', 'Landlord')
        self.agent, self.agent_token = make_user('agent_pv', 'Agent')
        self.tenant, _ = make_user('tenant_pv', 'Tenant')
        self.prop = make_property(self.landlord)
        self.unit = make_unit(self.prop, self.landlord)
        make_lease(self.unit, self.tenant)

    def auth(self, token):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

    def test_preview_requires_config_for_dates(self):
        self.auth(self.landlord_token)
        response = self.client.get(reverse('billing-preview', args=[self.prop.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['configured'])
        self.assertIsNone(response.data['next_invoice_generation_date'])

    def test_preview_with_config(self):
        BillingConfig.objects.create(
            property=self.prop,
            rent_due_day=15,
            grace_period_days=3,
            late_fee_percentage='5.00',
            invoice_lead_days=2,
            updated_by=self.landlord,
        )
        self.auth(self.landlord_token)
        response = self.client.get(reverse('billing-preview', args=[self.prop.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['configured'])
        self.assertEqual(response.data['invoice_lead_days'], 2)
        self.assertEqual(response.data['active_lease_count'], 1)

    def test_assigned_agent_can_preview(self):
        from property.models import PropertyAgent
        BillingConfig.objects.create(
            property=self.prop,
            rent_due_day=5,
            grace_period_days=0,
            late_fee_percentage='5.00',
            updated_by=self.landlord,
        )
        PropertyAgent.objects.create(property=self.prop, agent=self.agent, appointed_by=self.landlord)
        self.auth(self.agent_token)
        response = self.client.get(reverse('billing-preview', args=[self.prop.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class AdditionalIncomeTests(APITestCase):
    def setUp(self):
        self.landlord, self.landlord_token = make_user('landlord1', 'Landlord')
        self.other_landlord, self.other_token = make_user('landlord2', 'Landlord')
        self.prop = make_property(self.landlord)
        self.unit = make_unit(self.prop, self.landlord)
        self.charge_type = ChargeType.objects.create(property=self.prop, name='Water', created_by=self.landlord)

    def auth(self, token):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

    def test_landlord_can_record_additional_income(self):
        self.auth(self.landlord_token)
        data = {
            'unit': self.unit.id,
            'charge_type': self.charge_type.id,
            'amount': '1500.00',
            'date': str(date.today()),
            'description': 'March water',
        }
        response = self.client.post(reverse('additional-income-list', args=[self.prop.id]), data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['recorded_by'], self.landlord.id)

    def test_unit_from_wrong_property_rejected(self):
        other_prop = make_property(self.landlord)
        other_unit = make_unit(other_prop, self.landlord)
        self.auth(self.landlord_token)
        data = {
            'unit': other_unit.id,
            'charge_type': self.charge_type.id,
            'amount': '1500.00',
            'date': str(date.today()),
        }
        response = self.client.post(reverse('additional-income-list', args=[self.prop.id]), data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_charge_type_from_wrong_property_rejected(self):
        other_prop = make_property(self.landlord)
        other_ct = ChargeType.objects.create(property=other_prop, name='Water', created_by=self.landlord)
        self.auth(self.landlord_token)
        data = {
            'unit': self.unit.id,
            'charge_type': other_ct.id,
            'amount': '1500.00',
            'date': str(date.today()),
        }
        response = self.client.post(reverse('additional-income-list', args=[self.prop.id]), data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_other_landlord_cannot_access(self):
        self.auth(self.other_token)
        response = self.client.get(reverse('additional-income-list', args=[self.prop.id]))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_landlord_can_update_entry(self):
        entry = AdditionalIncome.objects.create(
            unit=self.unit, charge_type=self.charge_type,
            amount=Decimal('1500'), date=date.today(), recorded_by=self.landlord
        )
        self.auth(self.landlord_token)
        response = self.client.put(
            reverse('additional-income-detail', args=[self.prop.id, entry.id]),
            {'amount': '1750.00'}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Decimal(response.data['amount']), Decimal('1750.00'))

    def test_landlord_can_delete_entry(self):
        entry = AdditionalIncome.objects.create(
            unit=self.unit, charge_type=self.charge_type,
            amount=Decimal('1500'), date=date.today(), recorded_by=self.landlord
        )
        self.auth(self.landlord_token)
        response = self.client.delete(reverse('additional-income-detail', args=[self.prop.id, entry.id]))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)


class ExpenseTests(APITestCase):
    def setUp(self):
        self.landlord, self.landlord_token = make_user('landlord1', 'Landlord')
        self.other_landlord, self.other_token = make_user('landlord2', 'Landlord')
        self.prop = make_property(self.landlord)
        self.unit = make_unit(self.prop, self.landlord)

    def auth(self, token):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

    def test_landlord_can_record_expense(self):
        self.auth(self.landlord_token)
        data = {
            'category': 'insurance',
            'amount': '15000.00',
            'date': str(date.today()),
            'description': 'Annual insurance',
        }
        response = self.client.post(reverse('expense-list', args=[self.prop.id]), data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['category'], 'insurance')
        self.assertEqual(response.data['recorded_by'], self.landlord.id)

    def test_unit_from_wrong_property_rejected(self):
        other_prop = make_property(self.landlord)
        other_unit = make_unit(other_prop, self.landlord)
        self.auth(self.landlord_token)
        data = {
            'unit': other_unit.id,
            'category': 'utility',
            'amount': '3000.00',
            'date': str(date.today()),
        }
        response = self.client.post(reverse('expense-list', args=[self.prop.id]), data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_other_landlord_cannot_access(self):
        self.auth(self.other_token)
        response = self.client.get(reverse('expense-list', args=[self.prop.id]))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_landlord_can_list_expenses(self):
        Expense.objects.create(
            property=self.prop, category='tax', amount=Decimal('8000'),
            date=date.today(), recorded_by=self.landlord
        )
        self.auth(self.landlord_token)
        response = self.client.get(reverse('expense-list', args=[self.prop.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_landlord_can_update_expense(self):
        exp = Expense.objects.create(
            property=self.prop, category='tax', amount=Decimal('8000'),
            date=date.today(), recorded_by=self.landlord
        )
        self.auth(self.landlord_token)
        response = self.client.put(
            reverse('expense-detail', args=[self.prop.id, exp.id]),
            {'amount': '9000.00'}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Decimal(response.data['amount']), Decimal('9000.00'))

    def test_landlord_can_delete_expense(self):
        exp = Expense.objects.create(
            property=self.prop, category='other', amount=Decimal('500'),
            date=date.today(), recorded_by=self.landlord
        )
        self.auth(self.landlord_token)
        response = self.client.delete(reverse('expense-detail', args=[self.prop.id, exp.id]))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)


class FinancialReportTests(APITestCase):
    def setUp(self):
        self.landlord, self.landlord_token = make_user('landlord1', 'Landlord')
        self.other_landlord, self.other_token = make_user('landlord2', 'Landlord')
        self.tenant, self.tenant_token = make_user('tenant1', 'Tenant')
        self.prop = make_property(self.landlord)
        self.unit = make_unit(self.prop, self.landlord)
        self.lease = make_lease(self.unit, self.tenant)

        today = date.today()
        # Paid invoice this month
        self.invoice = Invoice.objects.create(
            lease=self.lease,
            period_start=today.replace(day=1),
            period_end=today,
            due_date=today,
            rent_amount=Decimal('45000'),
            late_fee_amount=Decimal('0'),
            total_amount=Decimal('45000'),
            status='paid',
        )
        self.payment = Payment.objects.create(
            invoice=self.invoice,
            amount=Decimal('45000'),
            stripe_payment_intent_id='pi_report_test',
            status='completed',
            paid_at=timezone.now(),
        )
        # Expense this month
        self.expense = Expense.objects.create(
            property=self.prop, category='utility', amount=Decimal('5000'),
            date=today, recorded_by=self.landlord
        )
        # Additional income this month
        self.charge_type = ChargeType.objects.create(property=self.prop, name='Water', created_by=self.landlord)
        self.ai = AdditionalIncome.objects.create(
            unit=self.unit, charge_type=self.charge_type,
            amount=Decimal('1500'), date=today, recorded_by=self.landlord
        )

    def auth(self, token):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

    def test_monthly_report_totals(self):
        today = date.today()
        self.auth(self.landlord_token)
        response = self.client.get(
            reverse('financial-report', args=[self.prop.id]),
            {'year': today.year, 'month': today.month}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['income']['total_collected'], '45000.00')
        self.assertEqual(response.data['income']['additional_income'], '1500.00')
        self.assertEqual(response.data['income']['total_income'], '46500.00')
        self.assertEqual(response.data['expenses']['total'], '5000.00')
        self.assertEqual(response.data['net_income'], '41500.00')
        self.assertEqual(response.data['occupancy']['occupied_units'], 1)
        self.assertEqual(response.data['occupancy']['total_units'], 1)
        self.assertEqual(response.data['occupancy']['occupancy_pct'], '100.00')
        self.assertEqual(response.data['occupancy_avg_pct'], '100.00')
        self.assertEqual(len(response.data['occupancy_series']), 1)

    def test_monthly_report_expense_by_category(self):
        today = date.today()
        self.auth(self.landlord_token)
        response = self.client.get(
            reverse('financial-report', args=[self.prop.id]),
            {'year': today.year, 'month': today.month}
        )
        self.assertIn('utility', response.data['expenses']['by_category'])

    def test_annual_report(self):
        today = date.today()
        self.auth(self.landlord_token)
        response = self.client.get(
            reverse('financial-report', args=[self.prop.id]),
            {'year': today.year}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['period'], str(today.year))
        self.assertIsNone(response.data['occupancy'])
        self.assertEqual(len(response.data['occupancy_series']), 12)
        self.assertIsNotNone(response.data['occupancy_avg_pct'])

    def test_monthly_occupancy_two_units_one_leased(self):
        make_unit(self.prop, self.landlord)
        today = date.today()
        self.auth(self.landlord_token)
        response = self.client.get(
            reverse('financial-report', args=[self.prop.id]),
            {'year': today.year, 'month': today.month}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['occupancy']['total_units'], 2)
        self.assertEqual(response.data['occupancy']['occupied_units'], 1)
        self.assertEqual(response.data['occupancy']['occupancy_pct'], '50.00')

    def test_monthly_occupancy_no_units(self):
        empty_prop = make_property(self.landlord)
        today = date.today()
        self.auth(self.landlord_token)
        response = self.client.get(
            reverse('financial-report', args=[empty_prop.id]),
            {'year': today.year, 'month': today.month}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['occupancy']['total_units'], 0)
        self.assertIsNone(response.data['occupancy']['occupancy_pct'])
        self.assertIsNone(response.data['occupancy_avg_pct'])

    def test_monthly_occupancy_only_leases_overlapping_period_count(self):
        self.lease.start_date = date(2024, 1, 1)
        self.lease.end_date = None
        self.lease.save()
        u2 = make_unit(self.prop, self.landlord)
        tenant2, _ = make_user('tenant2', 'Tenant')
        Lease.objects.create(
            unit=u2, tenant=tenant2, start_date=date(2023, 1, 1),
            end_date=date(2023, 12, 31), rent_amount=Decimal('30000'), is_active=False,
        )
        self.auth(self.landlord_token)
        response = self.client.get(
            reverse('financial-report', args=[self.prop.id]),
            {'year': 2024, 'month': 3}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['occupancy']['occupied_units'], 1)
        self.assertEqual(response.data['occupancy']['total_units'], 2)
        self.assertEqual(response.data['occupancy']['occupancy_pct'], '50.00')

    def test_year_required(self):
        self.auth(self.landlord_token)
        response = self.client.get(reverse('financial-report', args=[self.prop.id]))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_tenant_cannot_access_report(self):
        today = date.today()
        self.auth(self.tenant_token)
        response = self.client.get(
            reverse('financial-report', args=[self.prop.id]),
            {'year': today.year, 'month': today.month}
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_other_landlord_cannot_access_report(self):
        today = date.today()
        self.auth(self.other_token)
        response = self.client.get(
            reverse('financial-report', args=[self.prop.id]),
            {'year': today.year, 'month': today.month}
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class MaintenanceExpenseAutoCreateTests(APITestCase):
    """Expense is auto-created from accepted bid when request is marked completed."""

    def setUp(self):
        from authentication.models import ArtisanProfile
        from maintenance.models import MaintenanceBid
        self.landlord, self.landlord_token = make_user('landlord1', 'Landlord')
        self.tenant, self.tenant_token = make_user('tenant1', 'Tenant')
        self.artisan, self.artisan_token = make_user('artisan1', 'Artisan')
        ArtisanProfile.objects.create(user=self.artisan, trade='plumbing')

        self.prop = make_property(self.landlord)
        self.unit = make_unit(self.prop, self.landlord)
        lease = make_lease(self.unit, self.tenant)

        from maintenance.models import MaintenanceRequest
        self.req = MaintenanceRequest.objects.create(
            property=self.prop, unit=self.unit, submitted_by=self.tenant,
            title='Leaking tap', description='Dripping.', category='plumbing',
            priority='medium', status='in_progress', assigned_to=self.artisan,
        )
        self.bid = MaintenanceBid.objects.create(
            request=self.req, artisan=self.artisan,
            proposed_price=Decimal('8500'), status='accepted',
        )

    def auth(self, token):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

    def test_expense_auto_created_on_completion(self):
        self.auth(self.tenant_token)
        self.client.put(
            reverse('maintenance-request-detail', args=[self.req.id]),
            {'status': 'completed'}
        )
        exp = Expense.objects.filter(maintenance_request=self.req).first()
        self.assertIsNotNone(exp)
        self.assertEqual(exp.amount, Decimal('8500'))
        self.assertEqual(exp.category, 'maintenance')
        self.assertEqual(exp.property, self.prop)

    def test_no_expense_without_accepted_bid(self):
        self.bid.status = 'pending'
        self.bid.save()
        self.auth(self.tenant_token)
        self.client.put(
            reverse('maintenance-request-detail', args=[self.req.id]),
            {'status': 'completed'}
        )
        self.assertFalse(Expense.objects.filter(maintenance_request=self.req).exists())


class InvoiceNumberGenerationTests(APITestCase):
    def test_generate_invoice_number_format(self):
        self.assertEqual(generate_invoice_number(1), 'INV-0001')
        self.assertEqual(generate_invoice_number(35), 'INV-0035')
        self.assertEqual(generate_invoice_number(99999), 'INV-99999')

    def test_invoice_number_auto_assigned_on_create(self):
        landlord, _ = make_user('landlord_inv', 'Landlord')
        tenant, _ = make_user('tenant_inv', 'Tenant')
        prop = make_property(landlord)
        unit = make_unit(prop, landlord)
        lease = make_lease(unit, tenant)
        invoice = make_invoice(lease)
        invoice.refresh_from_db()
        self.assertEqual(invoice.invoice_number, f'INV-{invoice.pk:04d}')

    def test_invoice_number_unique(self):
        landlord, _ = make_user('landlord_inv2', 'Landlord')
        tenant, _ = make_user('tenant_inv2', 'Tenant')
        prop = make_property(landlord)
        unit = make_unit(prop, landlord)
        lease = make_lease(unit, tenant)

        inv1 = make_invoice(lease)
        inv1.refresh_from_db()

        unit2 = make_unit(prop, landlord)
        lease2 = Lease.objects.create(
            unit=unit2, tenant=tenant, start_date=date.today(),
            rent_amount='45000', is_active=True,
        )
        inv2 = make_invoice(lease2)
        inv2.refresh_from_db()

        self.assertNotEqual(inv1.invoice_number, inv2.invoice_number)

    def test_invoice_number_in_api_response(self):
        landlord, landlord_token = make_user('landlord_inv3', 'Landlord')
        tenant, tenant_token = make_user('tenant_inv3', 'Tenant')
        prop = make_property(landlord)
        unit = make_unit(prop, landlord)
        lease = make_lease(unit, tenant)
        invoice = make_invoice(lease)

        self.client.credentials(HTTP_AUTHORIZATION=f'Token {tenant_token.key}')
        response = self.client.get(reverse('invoice-detail', args=[invoice.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('invoice_number', response.data)
        self.assertTrue(response.data['invoice_number'].startswith('INV-'))

    def test_invoice_number_not_overwritten_on_update(self):
        landlord, _ = make_user('landlord_inv4', 'Landlord')
        tenant, _ = make_user('tenant_inv4', 'Tenant')
        prop = make_property(landlord)
        unit = make_unit(prop, landlord)
        lease = make_lease(unit, tenant)
        invoice = make_invoice(lease)
        invoice.refresh_from_db()
        original_number = invoice.invoice_number
        invoice.status = 'overdue'
        invoice.save()
        invoice.refresh_from_db()
        self.assertEqual(invoice.invoice_number, original_number)


class PaymentMethodChoicesTests(APITestCase):
    def test_valid_payment_method_choices(self):
        valid = ['mpesa', 'bank', 'card', 'cash', 'other']
        for method in valid:
            self.assertIn(method, dict(Payment.PAYMENT_METHOD_CHOICES))

    def test_payment_method_default_is_other(self):
        landlord, _ = make_user('landlord_pm', 'Landlord')
        tenant, _ = make_user('tenant_pm', 'Tenant')
        prop = make_property(landlord)
        unit = make_unit(prop, landlord)
        lease = make_lease(unit, tenant)
        invoice = make_invoice(lease)
        payment = Payment.objects.create(
            invoice=invoice,
            amount=Decimal('1000'),
            stripe_payment_intent_id='pi_pm_test',
            status='completed',
            paid_at=timezone.now(),
        )
        self.assertEqual(payment.payment_method, 'other')

    def test_payment_method_in_api_response(self):
        landlord, landlord_token = make_user('landlord_pm2', 'Landlord')
        tenant, tenant_token = make_user('tenant_pm2', 'Tenant')
        prop = make_property(landlord)
        unit = make_unit(prop, landlord)
        lease = make_lease(unit, tenant)
        invoice = make_invoice(lease, status='paid')
        Payment.objects.create(
            invoice=invoice,
            amount=Decimal('45000'),
            stripe_payment_intent_id='pi_pm_api',
            payment_method='card',
            transaction_reference='ch_abc123',
            status='completed',
            paid_at=timezone.now(),
        )
        Receipt.objects.create(
            payment=Payment.objects.get(stripe_payment_intent_id='pi_pm_api'),
            receipt_number='RCP-202604-9999',
        )
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {tenant_token.key}')
        response = self.client.get(reverse('receipt-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)

    def test_transaction_reference_stored(self):
        landlord, _ = make_user('landlord_tr', 'Landlord')
        tenant, _ = make_user('tenant_tr', 'Tenant')
        prop = make_property(landlord)
        unit = make_unit(prop, landlord)
        lease = make_lease(unit, tenant)
        invoice = make_invoice(lease)
        payment = Payment.objects.create(
            invoice=invoice,
            amount=Decimal('1000'),
            stripe_payment_intent_id='pi_tr_test',
            transaction_reference='TXN-ABC-123',
            status='completed',
            paid_at=timezone.now(),
        )
        payment.refresh_from_db()
        self.assertEqual(payment.transaction_reference, 'TXN-ABC-123')


class BackfillLogicTests(APITestCase):
    """Tests that verify the backfill data migration logic (run as Python functions)."""

    def test_backfill_payment_card_from_stripe(self):
        landlord, _ = make_user('landlord_bf1', 'Landlord')
        tenant, _ = make_user('tenant_bf1', 'Tenant')
        prop = make_property(landlord)
        unit = make_unit(prop, landlord)
        lease = make_lease(unit, tenant)
        invoice = make_invoice(lease)

        payment = Payment.objects.create(
            invoice=invoice,
            amount=Decimal('45000'),
            stripe_payment_intent_id='pi_real_stripe',
            stripe_charge_id='ch_real_stripe',
            status='completed',
            paid_at=timezone.now(),
        )
        self._run_payment_backfill(payment)
        payment.refresh_from_db()
        self.assertEqual(payment.payment_method, 'card')
        self.assertEqual(payment.transaction_reference, 'ch_real_stripe')

    def test_backfill_payment_manual_stays_other(self):
        landlord, _ = make_user('landlord_bf2', 'Landlord')
        tenant, _ = make_user('tenant_bf2', 'Tenant')
        prop = make_property(landlord)
        unit = make_unit(prop, landlord)
        lease = make_lease(unit, tenant)
        invoice = make_invoice(lease)

        payment = Payment.objects.create(
            invoice=invoice,
            amount=Decimal('45000'),
            stripe_payment_intent_id='manual-abc-123',
            status='completed',
            paid_at=timezone.now(),
        )
        self._run_payment_backfill(payment)
        payment.refresh_from_db()
        self.assertEqual(payment.payment_method, 'other')
        self.assertFalse(payment.transaction_reference)

    def test_backfill_invoice_number(self):
        landlord, _ = make_user('landlord_bf3', 'Landlord')
        tenant, _ = make_user('tenant_bf3', 'Tenant')
        prop = make_property(landlord)
        unit = make_unit(prop, landlord)
        lease = make_lease(unit, tenant)
        invoice = make_invoice(lease)
        invoice.refresh_from_db()
        self.assertTrue(invoice.invoice_number.startswith('INV-'))
        self.assertEqual(invoice.invoice_number, f'INV-{invoice.pk:04d}')

    @staticmethod
    def _run_payment_backfill(payment):
        """Simulate the backfill logic from the data migration."""
        changed = False
        if not payment.transaction_reference and payment.stripe_charge_id:
            payment.transaction_reference = payment.stripe_charge_id
            changed = True
        if payment.payment_method == 'other':
            if payment.stripe_payment_intent_id and not payment.stripe_payment_intent_id.startswith('manual-'):
                payment.payment_method = 'card'
                changed = True
            elif payment.stripe_charge_id:
                payment.payment_method = 'card'
                changed = True
        if changed:
            payment.save(update_fields=['payment_method', 'transaction_reference'])


class ReceiptEnrichmentTests(APITestCase):
    """Flattened receipt payload for receipts UI (list + detail)."""

    _EXPECTED_KEYS = frozenset({
        'id', 'payment', 'receipt_number', 'issued_at',
        'amount', 'payment_status', 'paid_at', 'payment_method',
        'transaction_ref', 'transaction_reference',
        'invoice_id', 'invoice_number', 'invoice_status',
        'invoice_period_start', 'invoice_period_end',
        'tenant_id', 'tenant_name', 'tenant_email',
        'unit_id', 'unit_name', 'property_id', 'property_name',
        'charge_type',
    })

    def setUp(self):
        self.landlord, self.landlord_token = make_user('landlord_rec_en', 'Landlord')
        self.tenant, self.tenant_token = make_user('tenant_rec_en', 'Tenant')
        self.tenant.first_name = 'Jane'
        self.tenant.last_name = 'Doe'
        self.tenant.email = 'jane.rec@example.com'
        self.tenant.save()

        self.prop = make_property(self.landlord)
        self.unit = make_unit(self.prop, self.landlord)
        self.lease = make_lease(self.unit, self.tenant)
        self.invoice = make_invoice(self.lease, status='paid')
        self.invoice.refresh_from_db()

        self.payment = Payment.objects.create(
            invoice=self.invoice,
            amount=Decimal('45000.00'),
            stripe_payment_intent_id='pi_enrich_1',
            stripe_charge_id='ch_enrich_1',
            payment_method='card',
            transaction_reference='',
            status='completed',
            paid_at=timezone.now(),
        )
        self.receipt = Receipt.objects.create(
            payment=self.payment,
            receipt_number='RCP-ENRICH-0001',
        )

    def test_receipt_detail_includes_all_flat_fields(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.tenant_token.key}')
        response = self.client.get(reverse('receipt-detail', args=[self.receipt.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self._EXPECTED_KEYS, set(response.data.keys()))
        self.assertEqual(response.data['payment'], self.payment.id)
        self.assertEqual(response.data['amount'], '45000.00')
        self.assertEqual(response.data['payment_status'], 'completed')
        self.assertEqual(response.data['payment_method'], 'card')
        self.assertEqual(response.data['transaction_ref'], 'ch_enrich_1')
        self.assertEqual(response.data['transaction_reference'], 'ch_enrich_1')
        self.assertEqual(response.data['invoice_id'], self.invoice.id)
        self.assertEqual(response.data['invoice_number'], self.invoice.invoice_number)
        self.assertEqual(response.data['invoice_status'], 'paid')
        self.assertEqual(response.data['tenant_id'], self.tenant.id)
        self.assertEqual(response.data['tenant_name'], 'Jane Doe')
        self.assertEqual(response.data['tenant_email'], 'jane.rec@example.com')
        self.assertEqual(response.data['unit_id'], self.unit.id)
        self.assertEqual(response.data['unit_name'], self.unit.name)
        self.assertEqual(response.data['property_id'], self.prop.id)
        self.assertEqual(response.data['property_name'], self.prop.name)
        self.assertEqual(response.data['charge_type'], 'Rent')

    def test_transaction_ref_prefers_transaction_reference(self):
        self.payment.transaction_reference = 'TXN-PREF-99'
        self.payment.save()
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.tenant_token.key}')
        response = self.client.get(reverse('receipt-detail', args=[self.receipt.id]))
        self.assertEqual(response.data['transaction_ref'], 'TXN-PREF-99')
        self.assertEqual(response.data['transaction_reference'], 'TXN-PREF-99')

    def test_tenant_name_falls_back_to_username(self):
        self.tenant.first_name = ''
        self.tenant.last_name = ''
        self.tenant.save()
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.tenant_token.key}')
        response = self.client.get(reverse('receipt-detail', args=[self.receipt.id]))
        self.assertEqual(response.data['tenant_name'], self.tenant.username)

    def test_charge_type_rent_plus_service_when_additional_income_in_period(self):
        ct = ChargeType.objects.create(property=self.prop, name='Water', created_by=self.landlord)
        AdditionalIncome.objects.create(
            unit=self.unit,
            charge_type=ct,
            amount=Decimal('500.00'),
            date=self.invoice.period_start,
            recorded_by=self.landlord,
        )
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.tenant_token.key}')
        response = self.client.get(reverse('receipt-detail', args=[self.receipt.id]))
        self.assertEqual(response.data['charge_type'], 'Rent + Service')

    def test_receipt_list_row_matches_detail_shape(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.tenant_token.key}')
        response = self.client.get(reverse('receipt-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(self._EXPECTED_KEYS, set(response.data['results'][0].keys()))
        self.assertEqual(response.data['results'][0]['receipt_number'], 'RCP-ENRICH-0001')

    def test_receipt_list_serializes_without_n_plus_one(self):
        def make_extra_receipt(month: int, seq: int):
            unit = make_unit(self.prop, self.landlord)
            lease = Lease.objects.create(
                unit=unit,
                tenant=self.tenant,
                start_date=date(2026, 1, 1),
                rent_amount='45000',
                is_active=True,
            )
            inv = Invoice.objects.create(
                lease=lease,
                period_start=date(2026, month, 1),
                period_end=date(2026, month, 28),
                due_date=date(2026, month, 5),
                rent_amount=Decimal('45000'),
                late_fee_amount=Decimal('0'),
                total_amount=Decimal('45000'),
                status='paid',
            )
            inv.refresh_from_db()
            pay = Payment.objects.create(
                invoice=inv,
                amount=Decimal('45000'),
                stripe_payment_intent_id=f'pi_enrich_{seq}',
                status='completed',
                paid_at=timezone.now(),
            )
            return Receipt.objects.create(payment=pay, receipt_number=f'RCP-ENRICH-{seq:04d}')

        for m, seq in zip(range(2, 6), range(2, 6)):
            make_extra_receipt(m, seq)

        qs = _receipt_base_queryset().filter(
            payment__invoice__lease__tenant=self.tenant,
        ).order_by('id')
        with self.assertNumQueries(1):
            rows = list(qs)
        self.assertEqual(len(rows), 5)
        with self.assertNumQueries(0):
            payload = ReceiptSerializer(rows, many=True).data
        self.assertEqual(len(payload), 5)
        for row in payload:
            self.assertEqual(self._EXPECTED_KEYS, set(row.keys()))


_RECEIPT_FILTER_DEFAULT_PAID_AT = object()


class ReceiptListFilterPaginationTests(APITestCase):
    """GET /api/billing/receipts/ query params, search, and DRF-style pagination."""

    def _create_receipt(
        self,
        landlord,
        tenant,
        prop,
        *,
        period_month,
        stripe_suffix,
        payment_method='card',
        paid_at=_RECEIPT_FILTER_DEFAULT_PAID_AT,
        receipt_number=None,
        unit=None,
        transaction_reference='',
    ):
        if unit is None:
            unit = make_unit(prop, landlord)
        lease = Lease.objects.create(
            unit=unit,
            tenant=tenant,
            start_date=date(2026, 1, 1),
            rent_amount='1000',
            is_active=True,
        )
        inv = Invoice.objects.create(
            lease=lease,
            period_start=date(2026, period_month, 1),
            period_end=date(2026, period_month, 28),
            due_date=date(2026, period_month, 5),
            rent_amount=Decimal('1000'),
            late_fee_amount=Decimal('0'),
            total_amount=Decimal('1000'),
            status='paid',
        )
        inv.refresh_from_db()
        if paid_at is _RECEIPT_FILTER_DEFAULT_PAID_AT:
            paid_at = timezone.make_aware(datetime(2026, period_month, 15, 12, 0, 0))
        pay = Payment.objects.create(
            invoice=inv,
            amount=Decimal('1000'),
            stripe_payment_intent_id=f'pi_filt_{stripe_suffix}',
            payment_method=payment_method,
            transaction_reference=transaction_reference or '',
            status='completed',
            paid_at=paid_at,
        )
        rn = receipt_number or f'RCP-FILT-{stripe_suffix}'
        return Receipt.objects.create(payment=pay, receipt_number=rn)

    def setUp(self):
        self.landlord, self.landlord_token = make_user('landlord_rf', 'Landlord')
        self.tenant, self.tenant_token = make_user('tenant_rf', 'Tenant')
        self.tenant.email = 'renter_rf@example.com'
        self.tenant.first_name = 'Pat'
        self.tenant.last_name = 'Customer'
        self.tenant.save()
        self.prop_a = make_property(self.landlord)
        self.prop_a.name = 'Alpha Plaza'
        self.prop_a.save()
        self.prop_b = make_property(self.landlord)
        self.prop_b.name = 'Beta Tower'
        self.prop_b.save()

    def auth(self, token):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

    def test_invalid_month_returns_400(self):
        self.auth(self.landlord_token)
        r = self.client.get(reverse('receipt-list'), {'month': '2026-13'})
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('month', r.data)
        r2 = self.client.get(reverse('receipt-list'), {'month': 'not-a-month'})
        self.assertEqual(r2.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_method_returns_400(self):
        self.auth(self.landlord_token)
        r = self.client.get(reverse('receipt-list'), {'method': 'bitcoin'})
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('method', r.data)

    def test_invalid_property_returns_400(self):
        self.auth(self.landlord_token)
        r = self.client.get(reverse('receipt-list'), {'property': 'x'})
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('property', r.data)

    def test_filter_by_property(self):
        self._create_receipt(self.landlord, self.tenant, self.prop_a, period_month=4, stripe_suffix='a1')
        self._create_receipt(self.landlord, self.tenant, self.prop_b, period_month=4, stripe_suffix='b1')
        self.auth(self.landlord_token)
        r = self.client.get(reverse('receipt-list'), {'property': self.prop_a.id})
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data['count'], 1)
        self.assertEqual(r.data['results'][0]['property_id'], self.prop_a.id)

    def test_filter_by_method(self):
        self._create_receipt(
            self.landlord, self.tenant, self.prop_a, period_month=3, stripe_suffix='c', payment_method='cash',
        )
        self._create_receipt(
            self.landlord, self.tenant, self.prop_a, period_month=3, stripe_suffix='d', payment_method='card',
        )
        self.auth(self.landlord_token)
        r = self.client.get(reverse('receipt-list'), {'method': 'cash'})
        self.assertEqual(r.data['count'], 1)
        self.assertEqual(r.data['results'][0]['payment_method'], 'cash')

    def test_filter_by_month_uses_paid_at(self):
        self._create_receipt(
            self.landlord,
            self.tenant,
            self.prop_a,
            period_month=5,
            stripe_suffix='e',
            paid_at=timezone.make_aware(datetime(2026, 6, 10, 12, 0, 0)),
        )
        self.auth(self.landlord_token)
        r_june = self.client.get(reverse('receipt-list'), {'month': '2026-06'})
        self.assertEqual(r_june.data['count'], 1)
        r_may = self.client.get(reverse('receipt-list'), {'month': '2026-05'})
        self.assertEqual(r_may.data['count'], 0)

    def test_filter_by_month_falls_back_to_issued_at_when_no_paid_at(self):
        rec = self._create_receipt(
            self.landlord,
            self.tenant,
            self.prop_a,
            period_month=4,
            stripe_suffix='f',
            paid_at=None,
        )
        issued = timezone.make_aware(datetime(2026, 7, 8, 9, 0, 0))
        Receipt.objects.filter(pk=rec.pk).update(issued_at=issued)
        self.auth(self.landlord_token)
        r = self.client.get(reverse('receipt-list'), {'month': '2026-07'})
        self.assertEqual(r.data['count'], 1)
        self.assertEqual(r.data['results'][0]['id'], rec.id)

    def test_search_receipt_number(self):
        self._create_receipt(
            self.landlord,
            self.tenant,
            self.prop_a,
            period_month=4,
            stripe_suffix='g',
            receipt_number='RCP-UNIQUE-XYZ',
        )
        self.auth(self.landlord_token)
        r = self.client.get(reverse('receipt-list'), {'search': 'UNIQUE-XYZ'})
        self.assertEqual(r.data['count'], 1)

    def test_search_tenant_email(self):
        self._create_receipt(self.landlord, self.tenant, self.prop_a, period_month=4, stripe_suffix='h')
        self.auth(self.landlord_token)
        r = self.client.get(reverse('receipt-list'), {'search': 'renter_rf@'})
        self.assertEqual(r.data['count'], 1)

    def test_search_tenant_full_name_concat(self):
        self._create_receipt(self.landlord, self.tenant, self.prop_a, period_month=4, stripe_suffix='h2')
        self.auth(self.landlord_token)
        r = self.client.get(reverse('receipt-list'), {'search': 'pat cust'})
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data['count'], 1)

    def test_search_invoice_number(self):
        rec = self._create_receipt(self.landlord, self.tenant, self.prop_a, period_month=4, stripe_suffix='i')
        inv_num = rec.payment.invoice.invoice_number
        self.auth(self.landlord_token)
        r = self.client.get(reverse('receipt-list'), {'search': inv_num})
        self.assertEqual(r.data['count'], 1)

    def test_search_transaction_reference(self):
        self._create_receipt(
            self.landlord,
            self.tenant,
            self.prop_a,
            period_month=4,
            stripe_suffix='j',
            transaction_reference='MPESA-REF-999',
        )
        self.auth(self.landlord_token)
        r = self.client.get(reverse('receipt-list'), {'search': 'mpesa-ref'})
        self.assertEqual(r.data['count'], 1)

    def test_search_unit_name(self):
        unit = make_unit(self.prop_a, self.landlord)
        unit.name = 'Penthouse A'
        unit.save()
        self._create_receipt(
            self.landlord, self.tenant, self.prop_a, period_month=4, stripe_suffix='k', unit=unit,
        )
        self.auth(self.landlord_token)
        r = self.client.get(reverse('receipt-list'), {'search': 'penthouse'})
        self.assertEqual(r.data['count'], 1)

    def test_combined_filters(self):
        self._create_receipt(
            self.landlord,
            self.tenant,
            self.prop_a,
            period_month=4,
            stripe_suffix='m1',
            payment_method='mpesa',
            paid_at=timezone.make_aware(datetime(2026, 4, 20, 12, 0, 0)),
        )
        self._create_receipt(
            self.landlord,
            self.tenant,
            self.prop_a,
            period_month=4,
            stripe_suffix='m2',
            payment_method='card',
            paid_at=timezone.make_aware(datetime(2026, 4, 21, 12, 0, 0)),
        )
        self.auth(self.landlord_token)
        r = self.client.get(
            reverse('receipt-list'),
            {'property': self.prop_a.id, 'method': 'mpesa', 'month': '2026-04'},
        )
        self.assertEqual(r.data['count'], 1)
        self.assertEqual(r.data['results'][0]['payment_method'], 'mpesa')

    def test_pagination_shape(self):
        for n in range(15):
            self._create_receipt(
                self.landlord, self.tenant, self.prop_a, period_month=2, stripe_suffix=f'p{n}',
            )
        self.auth(self.landlord_token)
        r = self.client.get(reverse('receipt-list'), {'page': 1, 'page_size': 10})
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data['count'], 15)
        self.assertEqual(len(r.data['results']), 10)
        self.assertIsNotNone(r.data['next'])
        r2 = self.client.get(reverse('receipt-list'), {'page': 2, 'page_size': 10})
        self.assertEqual(len(r2.data['results']), 5)
        self.assertIsNone(r2.data['next'])

    def test_page_size_capped(self):
        with patch.object(ReceiptListPagination, 'max_page_size', 5):
            for n in range(12):
                self._create_receipt(
                    self.landlord, self.tenant, self.prop_a, period_month=3, stripe_suffix=f'cap{n}',
                )
            self.auth(self.landlord_token)
            r = self.client.get(reverse('receipt-list'), {'page': 1, 'page_size': 500})
            self.assertEqual(len(r.data['results']), 5)
            self.assertEqual(r.data['count'], 12)

    def test_tenant_other_property_filter_returns_empty(self):
        other_landlord, _ = make_user('landlord_other_rf', 'Landlord')
        other_prop = make_property(other_landlord)
        self._create_receipt(self.landlord, self.tenant, self.prop_a, period_month=4, stripe_suffix='oz1')
        self.auth(self.tenant_token)
        r = self.client.get(reverse('receipt-list'), {'property': other_prop.id})
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data['count'], 0)
        self.assertEqual(len(r.data['results']), 0)


class ReceiptStatsTests(APITestCase):
    """GET /api/billing/receipts/stats/"""

    def _pay_rec(
        self,
        landlord,
        tenant,
        prop,
        *,
        inv_month,
        paid_dt,
        amount,
        method='card',
        suffix='x',
    ):
        unit = make_unit(prop, landlord)
        lease = Lease.objects.create(
            unit=unit,
            tenant=tenant,
            start_date=date(2026, 1, 1),
            rent_amount=str(amount),
            is_active=True,
        )
        inv = Invoice.objects.create(
            lease=lease,
            period_start=date(2026, inv_month, 1),
            period_end=date(2026, inv_month, 28),
            due_date=date(2026, inv_month, 5),
            rent_amount=Decimal(str(amount)),
            late_fee_amount=Decimal('0'),
            total_amount=Decimal(str(amount)),
            status='paid',
        )
        inv.refresh_from_db()
        pay = Payment.objects.create(
            invoice=inv,
            amount=Decimal(str(amount)),
            stripe_payment_intent_id=f'pi_st_{suffix}_{amount}_{method}',
            payment_method=method,
            status='completed',
            paid_at=paid_dt,
        )
        return Receipt.objects.create(payment=pay, receipt_number=f'RCP-ST-{suffix}-{pay.id}')

    @patch('billing.receipt_stats.timezone.now')
    def test_normal_dataset(self, mock_now):
        mock_now.return_value = timezone.make_aware(datetime(2026, 4, 20, 12, 0, 0))
        landlord, lt = make_user('landlord_st1', 'Landlord')
        tenant, _ = make_user('tenant_st1', 'Tenant')
        prop = make_property(landlord)
        self._pay_rec(
            landlord, tenant, prop, inv_month=3,
            paid_dt=timezone.make_aware(datetime(2026, 3, 10, 12, 0, 0)),
            amount='100', method='card', suffix='a',
        )
        self._pay_rec(
            landlord, tenant, prop, inv_month=3,
            paid_dt=timezone.make_aware(datetime(2026, 3, 11, 12, 0, 0)),
            amount='200', method='card', suffix='b',
        )
        self._pay_rec(
            landlord, tenant, prop, inv_month=3,
            paid_dt=timezone.make_aware(datetime(2026, 3, 12, 12, 0, 0)),
            amount='300', method='mpesa', suffix='c',
        )
        self._pay_rec(
            landlord, tenant, prop, inv_month=4,
            paid_dt=timezone.make_aware(datetime(2026, 4, 5, 12, 0, 0)),
            amount='400', method='card', suffix='d',
        )
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {lt.key}')
        r = self.client.get(reverse('receipt-stats'))
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data['total_count'], 4)
        self.assertEqual(Decimal(r.data['average_amount']), Decimal('250.00'))
        self.assertEqual(r.data['this_month_count'], 1)
        self.assertEqual(Decimal(r.data['this_month_total']), Decimal('400.00'))
        bd = r.data['method_breakdown']
        self.assertAlmostEqual(bd['card'], 75.0, places=5)
        self.assertAlmostEqual(bd['mpesa'], 25.0, places=5)
        self.assertEqual(bd['bank'], 0.0)
        self.assertEqual(bd['cash'], 0.0)
        self.assertEqual(bd['other'], 0.0)

    def test_empty_dataset(self):
        landlord, lt = make_user('landlord_st_empty', 'Landlord')
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {lt.key}')
        r = self.client.get(reverse('receipt-stats'))
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data['total_count'], 0)
        self.assertEqual(r.data['this_month_count'], 0)
        self.assertEqual(r.data['this_month_total'], '0.00')
        self.assertEqual(r.data['average_amount'], '0.00')
        for k, v in r.data['method_breakdown'].items():
            self.assertEqual(v, 0.0, k)

    @patch('billing.receipt_stats.timezone.now')
    def test_property_filter(self, mock_now):
        mock_now.return_value = timezone.make_aware(datetime(2026, 4, 1, 12, 0, 0))
        landlord, lt = make_user('landlord_st_pf', 'Landlord')
        tenant, _ = make_user('tenant_st_pf', 'Tenant')
        pa = make_property(landlord)
        pb = make_property(landlord)
        self._pay_rec(
            landlord, tenant, pa, inv_month=4,
            paid_dt=timezone.make_aware(datetime(2026, 4, 2, 12, 0, 0)),
            amount='1000', suffix='p1',
        )
        self._pay_rec(
            landlord, tenant, pa, inv_month=4,
            paid_dt=timezone.make_aware(datetime(2026, 4, 3, 12, 0, 0)),
            amount='2000', suffix='p2',
        )
        self._pay_rec(
            landlord, tenant, pb, inv_month=4,
            paid_dt=timezone.make_aware(datetime(2026, 4, 4, 12, 0, 0)),
            amount='5000', suffix='p3',
        )
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {lt.key}')
        r = self.client.get(reverse('receipt-stats'), {'property': pa.id})
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data['total_count'], 2)
        self.assertEqual(Decimal(r.data['average_amount']), Decimal('1500.00'))

    @patch('billing.receipt_stats.timezone.now')
    def test_month_query_filter(self, mock_now):
        mock_now.return_value = timezone.make_aware(datetime(2026, 5, 1, 12, 0, 0))
        landlord, lt = make_user('landlord_st_mo', 'Landlord')
        tenant, _ = make_user('tenant_st_mo', 'Tenant')
        prop = make_property(landlord)
        self._pay_rec(
            landlord, tenant, prop, inv_month=3,
            paid_dt=timezone.make_aware(datetime(2026, 3, 15, 12, 0, 0)),
            amount='100', suffix='m1',
        )
        self._pay_rec(
            landlord, tenant, prop, inv_month=4,
            paid_dt=timezone.make_aware(datetime(2026, 4, 15, 12, 0, 0)),
            amount='200', suffix='m2',
        )
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {lt.key}')
        r = self.client.get(reverse('receipt-stats'), {'month': '2026-03'})
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data['total_count'], 1)
        self.assertEqual(Decimal(r.data['average_amount']), Decimal('100.00'))
        self.assertEqual(r.data['this_month_count'], 0)

    def test_invalid_month_returns_400(self):
        landlord, lt = make_user('landlord_st_inv', 'Landlord')
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {lt.key}')
        r = self.client.get(reverse('receipt-stats'), {'month': '2026-13'})
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('month', r.data)

    def test_invalid_property_returns_400(self):
        landlord, lt = make_user('landlord_st_ip', 'Landlord')
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {lt.key}')
        r = self.client.get(reverse('receipt-stats'), {'property': 'nope'})
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('property', r.data)

    def test_tenant_scoping_other_tenant_sees_empty(self):
        landlord, _ = make_user('landlord_st_sc', 'Landlord')
        t1, t1tok = make_user('tenant_st_t1', 'Tenant')
        t2, t2tok = make_user('tenant_st_t2', 'Tenant')
        prop = make_property(landlord)
        self._pay_rec(
            landlord, t1, prop, inv_month=4,
            paid_dt=timezone.make_aware(datetime(2026, 4, 1, 12, 0, 0)),
            amount='50', suffix='s1',
        )
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {t2tok.key}')
        r = self.client.get(reverse('receipt-stats'))
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data['total_count'], 0)

    def test_agent_scoping_only_assigned_properties(self):
        landlord, _ = make_user('landlord_st_ag', 'Landlord')
        agent, atok = make_user('agent_st_ag', 'Agent')
        tenant, _ = make_user('tenant_st_ag', 'Tenant')
        pa = make_property(landlord)
        pb = make_property(landlord)
        PropertyAgent.objects.create(property=pa, agent=agent, appointed_by=landlord)
        self._pay_rec(
            landlord, tenant, pa, inv_month=4,
            paid_dt=timezone.make_aware(datetime(2026, 4, 1, 12, 0, 0)),
            amount='100', suffix='ag1',
        )
        self._pay_rec(
            landlord, tenant, pb, inv_month=4,
            paid_dt=timezone.make_aware(datetime(2026, 4, 2, 12, 0, 0)),
            amount='900', suffix='ag2',
        )
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {atok.key}')
        r = self.client.get(reverse('receipt-stats'))
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data['total_count'], 1)
        self.assertEqual(Decimal(r.data['average_amount']), Decimal('100.00'))
