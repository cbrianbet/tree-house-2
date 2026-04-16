"""
API contract tests: receipts list, detail, and stats match frontend expectations.
"""
from datetime import date, datetime
from decimal import Decimal
from unittest.mock import patch

from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APIRequestFactory, APITestCase, force_authenticate

from billing.models import Payment
from billing.views import receipt_list, receipt_stats
from billing.receipt_contract_factories import (
    contract_create_paid_receipt,
    contract_make_user,
    contract_property_unit_lease,
)


RECEIPT_ENRICHED_KEYS = frozenset({
    'amount', 'fee_amount', 'payment_status', 'paid_at', 'payment_method', 'transaction_ref',
    'transaction_reference', 'invoice_id', 'invoice_number', 'invoice_status',
    'invoice_period_start', 'invoice_period_end', 'tenant_id', 'tenant_name',
    'tenant_email', 'unit_id', 'unit_name', 'property_id', 'property_name', 'charge_type',
})
RECEIPT_LEGACY_KEYS = frozenset({'id', 'payment', 'receipt_number', 'issued_at'})
RECEIPT_ALL_KEYS = RECEIPT_ENRICHED_KEYS | RECEIPT_LEGACY_KEYS

STATS_ROOT_KEYS = frozenset({
    'total_count', 'this_month_count', 'this_month_total', 'method_breakdown', 'average_amount',
})
METHOD_BREAKDOWN_KEYS = frozenset({c[0] for c in Payment.PAYMENT_METHOD_CHOICES})

# List view: COUNT + SELECT page; allow headroom for DB/version variance without permitting N+1.
RECEIPT_LIST_MAX_QUERIES = 12


def _assert_receipt_payload_contract(testcase, payload: dict):
    missing = RECEIPT_ALL_KEYS - set(payload.keys())
    testcase.assertFalse(missing, f'Missing receipt keys: {sorted(missing)}')
    extra = set(payload.keys()) - RECEIPT_ALL_KEYS
    testcase.assertFalse(extra, f'Unexpected extra keys: {sorted(extra)}')


def _assert_stats_schema(testcase, data: dict):
    testcase.assertEqual(set(data.keys()), STATS_ROOT_KEYS, 'Stats root keys mismatch')
    testcase.assertIsInstance(data['total_count'], int)
    testcase.assertIsInstance(data['this_month_count'], int)
    testcase.assertIsInstance(data['this_month_total'], str)
    testcase.assertIsInstance(data['average_amount'], str)
    testcase.assertIsInstance(data['method_breakdown'], dict)
    testcase.assertEqual(set(data['method_breakdown'].keys()), METHOD_BREAKDOWN_KEYS)
    for k in METHOD_BREAKDOWN_KEYS:
        testcase.assertIsInstance(data['method_breakdown'][k], (int, float))


class ReceiptsApiContractTests(APITestCase):
    """Frontend contract for /api/billing/receipts/ and /api/billing/receipts/stats/."""

    def setUp(self):
        self.client = APIClient()
        self.landlord, self.landlord_token = contract_make_user('contract_ll', 'Landlord')
        self.tenant, self.tenant_token = contract_make_user('contract_tt', 'Tenant')
        self.tenant.first_name = 'Sam'
        self.tenant.last_name = 'Renter'
        self.tenant.email = 'sam.renter@contract.test'
        self.tenant.save()
        self.prop, self.unit, self.lease = contract_property_unit_lease(
            self.landlord, self.tenant, property_name='Contract Tower', unit_name='Floor 2',
        )
        self.receipt = contract_create_paid_receipt(
            self.lease,
            period_month=4,
            amount='1500.00',
            payment_method='card',
            receipt_number='RCP-CONTRACT-PRIMARY',
            paid_at=timezone_nowish(),
            transaction_reference='TXN-CONTRACT-1',
        )

    def auth_landlord(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.landlord_token.key}')


def timezone_nowish():
    from django.utils import timezone
    return timezone.make_aware(datetime(2026, 4, 16, 14, 30, 0))


class ReceiptListContractTests(ReceiptsApiContractTests):
    def test_list_page_query_params_contract(self):
        self.auth_landlord()
        url = reverse('receipt-list')
        r = self.client.get(url, {'page': '1', 'page_size': '15'})
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        for key in ('count', 'next', 'previous', 'results'):
            self.assertIn(key, r.data, f'Pagination missing {key}')
        self.assertIsInstance(r.data['count'], int)
        self.assertIsInstance(r.data['results'], list)
        self.assertGreaterEqual(len(r.data['results']), 1)
        for item in r.data['results']:
            _assert_receipt_payload_contract(self, item)

    def test_detail_contract(self):
        self.auth_landlord()
        r = self.client.get(reverse('receipt-detail', args=[self.receipt.id]))
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        _assert_receipt_payload_contract(self, r.data)
        self.assertEqual(r.data['receipt_number'], 'RCP-CONTRACT-PRIMARY')
        self.assertEqual(r.data['transaction_ref'], 'TXN-CONTRACT-1')
        self.assertEqual(r.data['transaction_reference'], 'TXN-CONTRACT-1')

    def test_filter_property(self):
        _, _, lease_b = contract_property_unit_lease(
            self.landlord, self.tenant, property_name='Other Building', unit_name='U9',
        )
        contract_create_paid_receipt(lease_b, period_month=4, amount='500', payment_method='cash')
        self.auth_landlord()
        r = self.client.get(reverse('receipt-list'), {'property': self.prop.id})
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data['count'], 1)
        self.assertEqual(r.data['results'][0]['property_id'], self.prop.id)

    def test_filter_method(self):
        contract_create_paid_receipt(
            self.lease,
            period_month=5,
            amount='200',
            payment_method='mpesa',
            receipt_number='RCP-MPE',
        )
        self.auth_landlord()
        r = self.client.get(reverse('receipt-list'), {'method': 'mpesa'})
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data['count'], 1)
        self.assertEqual(r.data['results'][0]['payment_method'], 'mpesa')

    def test_filter_month(self):
        contract_create_paid_receipt(
            self.lease,
            period_month=6,
            amount='300',
            payment_method='bank',
            paid_at=datetime_to_aware(2026, 6, 5),
            receipt_number='RCP-JUN',
        )
        self.auth_landlord()
        r = self.client.get(reverse('receipt-list'), {'month': '2026-06'})
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data['count'], 1)
        self.assertEqual(r.data['results'][0]['receipt_number'], 'RCP-JUN')

    def test_filter_search(self):
        self.auth_landlord()
        r = self.client.get(reverse('receipt-list'), {'search': 'CONTRACT-PRIMARY'})
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data['count'], 1)

    def test_filters_combined(self):
        contract_create_paid_receipt(
            self.lease,
            period_month=3,
            amount='100',
            payment_method='mpesa',
            receipt_number='RCP-SPEC-ALPHA',
            paid_at=datetime_to_aware(2026, 3, 12),
        )
        contract_create_paid_receipt(
            self.lease,
            year=2027,
            period_month=3,
            amount='100',
            payment_method='mpesa',
            receipt_number='RCP-SPEC-BETA',
            paid_at=datetime_to_aware(2026, 3, 13),
        )
        contract_create_paid_receipt(
            self.lease,
            year=2027,
            period_month=4,
            amount='100',
            payment_method='card',
            receipt_number='RCP-SPEC-GAMMA',
            paid_at=datetime_to_aware(2026, 4, 1),
        )
        self.auth_landlord()
        r = self.client.get(
            reverse('receipt-list'),
            {
                'property': self.prop.id,
                'method': 'mpesa',
                'month': '2026-03',
                'search': 'ALPHA',
            },
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data['count'], 1)
        self.assertEqual(r.data['results'][0]['receipt_number'], 'RCP-SPEC-ALPHA')

    def test_list_bounded_query_count(self):
        for i in range(12):
            month = i + 1
            contract_create_paid_receipt(
                self.lease,
                year=2027,
                period_month=month,
                amount='10',
                payment_method='other',
                receipt_number=f'RCP-BENCH-{month}-{i}',
                paid_at=datetime_to_aware(2027, month, 5),
            )
        factory = APIRequestFactory()
        request = factory.get('/api/billing/receipts/', {'page': '1', 'page_size': '15'})
        force_authenticate(request, user=self.landlord)
        with CaptureQueriesContext(connection) as ctx:
            response = receipt_list(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        n = len(ctx.captured_queries)
        self.assertLessEqual(
            n,
            RECEIPT_LIST_MAX_QUERIES,
            f'List view used {n} queries (cap {RECEIPT_LIST_MAX_QUERIES}); possible N+1',
        )


def datetime_to_aware(y, mo, d):
    from django.utils import timezone as dj_tz
    return dj_tz.make_aware(datetime(y, mo, d, 12, 0, 0))


class ReceiptStatsContractTests(ReceiptsApiContractTests):
    @patch('billing.receipt_stats.timezone.now')
    def test_stats_exact_schema_and_percentage_sum(self, mock_now):
        mock_now.return_value = datetime_to_aware(2026, 4, 20)
        contract_create_paid_receipt(
            self.lease, period_month=5, amount='100', payment_method='card',
            receipt_number='RCP-ST-A', paid_at=datetime_to_aware(2026, 4, 1),
        )
        contract_create_paid_receipt(
            self.lease, period_month=6, amount='100', payment_method='card',
            receipt_number='RCP-ST-B', paid_at=datetime_to_aware(2026, 4, 2),
        )
        contract_create_paid_receipt(
            self.lease, period_month=7, amount='200', payment_method='mpesa',
            receipt_number='RCP-ST-C', paid_at=datetime_to_aware(2026, 4, 3),
        )
        self.auth_landlord()
        r = self.client.get(reverse('receipt-stats'))
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        _assert_stats_schema(self, r.data)
        self.assertEqual(r.data['total_count'], 4)
        pct_sum = sum(r.data['method_breakdown'].values())
        self.assertAlmostEqual(pct_sum, 100.0, delta=0.05)
        self.assertRegex(r.data['average_amount'], r'^\d+\.\d{2}$')
        self.assertRegex(r.data['this_month_total'], r'^\d+\.\d{2}$')

    def test_stats_empty_still_matches_schema(self):
        lone_landlord, tok = contract_make_user('contract_empty_ll', 'Landlord')
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {tok.key}')
        r = self.client.get(reverse('receipt-stats'))
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        _assert_stats_schema(self, r.data)
        self.assertEqual(r.data['total_count'], 0)
        self.assertEqual(sum(r.data['method_breakdown'].values()), 0.0)
