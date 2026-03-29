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
from billing.models import BillingConfig, Invoice, Payment, Receipt, ReminderLog
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
