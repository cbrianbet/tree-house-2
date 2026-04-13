import calendar
from datetime import date, timedelta
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
from billing.models import BillingConfig, Invoice, Payment, Receipt, ReminderLog, ChargeType, AdditionalIncome, Expense
from billing.utils import generate_receipt_number

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

    def test_get_config_not_found(self):
        self.auth(self.landlord_token)
        response = self.client.get(reverse('billing-config', args=[self.prop.id]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


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

    def test_landlord_records_full_payment(self):
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
        self.assertEqual(len(response.data), 1)

    def test_tenant_can_retrieve_receipt(self):
        self.auth(self.tenant_token)
        response = self.client.get(reverse('receipt-detail', args=[self.receipt.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['receipt_number'], 'RCP-202603-0001')

    def test_landlord_can_list_receipts(self):
        self.auth(self.landlord_token)
        response = self.client.get(reverse('receipt-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)


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

    @patch('billing.management.commands.process_billing.send_mail')
    def test_pre_due_reminder_sent(self, mock_mail):
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
        mock_mail.assert_called()
        self.assertTrue(ReminderLog.objects.filter(invoice=invoice, reminder_type='pre_due').exists())

    @patch('billing.management.commands.process_billing.send_mail')
    def test_reminder_not_sent_twice(self, mock_mail):
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
        mock_mail.assert_not_called()


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
