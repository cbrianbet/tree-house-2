from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token

from authentication.models import CustomUser, Role
from .models import SystemMetric, AlertRule, AlertInstance


def make_user(username, role_name):
    role, _ = Role.objects.get_or_create(name=role_name)
    return CustomUser.objects.create_user(
        username=username,
        password='testpass123',
        email=f'{username}@test.com',
        role=role,
        first_name='Test',
        last_name='User',
    )


def make_admin(username):
    role, _ = Role.objects.get_or_create(name=Role.ADMIN)
    return CustomUser.objects.create_user(
        username=username,
        password='testpass123',
        email=f'{username}@test.com',
        role=role,
        first_name='Admin',
        last_name='User',
        is_staff=True,
    )


def make_rule(admin, **kwargs):
    defaults = {
        'name': 'Test Rule',
        'metric_type': 'overdue_invoice_count',
        'condition': 'gte',
        'threshold_value': 10,
        'severity': 'warning',
        'created_by': admin,
    }
    defaults.update(kwargs)
    return AlertRule.objects.create(**defaults)


class MetricListTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = make_admin('admin_m')
        self.admin_token = Token.objects.create(user=self.admin)
        self.tenant = make_user('tenant_m', Role.TENANT)
        self.tenant_token = Token.objects.create(user=self.tenant)
        SystemMetric.objects.create(metric_type='overdue_invoice_count', value=5)
        SystemMetric.objects.create(metric_type='monthly_revenue', value=150000)

    def test_admin_can_list(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.admin_token.key}')
        response = self.client.get('/api/monitoring/metrics/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)

    def test_non_admin_forbidden(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.tenant_token.key}')
        response = self.client.get('/api/monitoring/metrics/')
        self.assertEqual(response.status_code, 403)

    def test_unauthenticated_denied(self):
        response = self.client.get('/api/monitoring/metrics/')
        self.assertEqual(response.status_code, 401)

    def test_filter_by_metric_type(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.admin_token.key}')
        response = self.client.get('/api/monitoring/metrics/?metric_type=overdue_invoice_count')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['metric_type'], 'overdue_invoice_count')

    def test_hours_filter_excludes_old_metrics(self):
        # All metrics just created — should appear within 1 hour window
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.admin_token.key}')
        response = self.client.get('/api/monitoring/metrics/?hours=1')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)


class AlertRuleListCreateTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = make_admin('admin_r')
        self.admin_token = Token.objects.create(user=self.admin)
        self.tenant = make_user('tenant_r', Role.TENANT)
        self.tenant_token = Token.objects.create(user=self.tenant)

    def test_admin_can_list_rules(self):
        rule = make_rule(self.admin)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.admin_token.key}')
        response = self.client.get('/api/monitoring/alert-rules/')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(len(response.data) >= 1)
        names = [r['name'] for r in response.data]
        self.assertIn(rule.name, names)

    def test_non_admin_cannot_list(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.tenant_token.key}')
        response = self.client.get('/api/monitoring/alert-rules/')
        self.assertEqual(response.status_code, 403)

    def test_admin_can_create_rule(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.admin_token.key}')
        data = {
            'name': 'High overdue',
            'metric_type': 'overdue_invoice_count',
            'condition': 'gt',
            'threshold_value': '15.00',
            'severity': 'warning',
            'enabled': True,
        }
        response = self.client.post('/api/monitoring/alert-rules/', data, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['name'], 'High overdue')
        self.assertEqual(response.data['created_by'], self.admin.pk)

    def test_non_admin_cannot_create(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.tenant_token.key}')
        response = self.client.post(
            '/api/monitoring/alert-rules/',
            {'name': 'x', 'metric_type': 'overdue_invoice_count', 'condition': 'gt',
             'threshold_value': '5.00', 'severity': 'warning'},
            format='json',
        )
        self.assertEqual(response.status_code, 403)

    def test_create_rule_missing_field_returns_400(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.admin_token.key}')
        response = self.client.post(
            '/api/monitoring/alert-rules/',
            {'name': 'Missing fields'},
            format='json',
        )
        self.assertEqual(response.status_code, 400)


class AlertRuleDetailTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = make_admin('admin_rd')
        self.admin_token = Token.objects.create(user=self.admin)
        self.tenant = make_user('tenant_rd', Role.TENANT)
        self.tenant_token = Token.objects.create(user=self.tenant)
        self.rule = make_rule(self.admin)

    def test_admin_can_retrieve(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.admin_token.key}')
        response = self.client.get(f'/api/monitoring/alert-rules/{self.rule.pk}/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['name'], self.rule.name)

    def test_admin_can_patch(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.admin_token.key}')
        response = self.client.patch(
            f'/api/monitoring/alert-rules/{self.rule.pk}/',
            {'enabled': False},
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data['enabled'])

    def test_admin_can_delete(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.admin_token.key}')
        response = self.client.delete(f'/api/monitoring/alert-rules/{self.rule.pk}/')
        self.assertEqual(response.status_code, 204)
        self.assertFalse(AlertRule.objects.filter(pk=self.rule.pk).exists())

    def test_non_admin_forbidden(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.tenant_token.key}')
        response = self.client.get(f'/api/monitoring/alert-rules/{self.rule.pk}/')
        self.assertEqual(response.status_code, 403)

    def test_404_on_missing_rule(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.admin_token.key}')
        response = self.client.get('/api/monitoring/alert-rules/9999/')
        self.assertEqual(response.status_code, 404)


class AlertListTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = make_admin('admin_al')
        self.admin_token = Token.objects.create(user=self.admin)
        self.tenant = make_user('tenant_al', Role.TENANT)
        self.tenant_token = Token.objects.create(user=self.tenant)

        self.rule = make_rule(self.admin)
        self.alert = AlertInstance.objects.create(rule=self.rule, triggered_value=15)

    def test_admin_can_list(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.admin_token.key}')
        response = self.client.get('/api/monitoring/alerts/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

    def test_non_admin_forbidden(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.tenant_token.key}')
        response = self.client.get('/api/monitoring/alerts/')
        self.assertEqual(response.status_code, 403)

    def test_filter_by_status(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.admin_token.key}')
        response = self.client.get('/api/monitoring/alerts/?status=triggered')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

        response = self.client.get('/api/monitoring/alerts/?status=resolved')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 0)

    def test_filter_by_severity(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.admin_token.key}')
        response = self.client.get('/api/monitoring/alerts/?severity=warning')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

        response = self.client.get('/api/monitoring/alerts/?severity=critical')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 0)


class AlertDetailTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = make_admin('admin_ad')
        self.admin_token = Token.objects.create(user=self.admin)
        self.tenant = make_user('tenant_ad', Role.TENANT)
        self.tenant_token = Token.objects.create(user=self.tenant)

        self.rule = make_rule(self.admin)
        self.alert = AlertInstance.objects.create(rule=self.rule, triggered_value=15)

    def test_admin_can_retrieve(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.admin_token.key}')
        response = self.client.get(f'/api/monitoring/alerts/{self.alert.pk}/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['status'], 'triggered')

    def test_non_admin_forbidden(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.tenant_token.key}')
        response = self.client.get(f'/api/monitoring/alerts/{self.alert.pk}/')
        self.assertEqual(response.status_code, 403)

    def test_acknowledge_alert(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.admin_token.key}')
        response = self.client.patch(
            f'/api/monitoring/alerts/{self.alert.pk}/',
            {'status': 'acknowledged', 'note': 'Looking into it'},
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['status'], 'acknowledged')
        self.assertEqual(response.data['note'], 'Looking into it')
        self.assertEqual(response.data['acknowledged_by'], self.admin.pk)
        self.assertIsNotNone(response.data['acknowledged_at'])

    def test_resolve_alert(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.admin_token.key}')
        response = self.client.patch(
            f'/api/monitoring/alerts/{self.alert.pk}/',
            {'status': 'resolved', 'note': 'Fixed'},
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['status'], 'resolved')
        self.assertIsNotNone(response.data['resolved_at'])

    def test_invalid_transition_from_resolved(self):
        self.alert.status = 'resolved'
        self.alert.save()
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.admin_token.key}')
        response = self.client.patch(
            f'/api/monitoring/alerts/{self.alert.pk}/',
            {'status': 'triggered'},
            format='json',
        )
        self.assertEqual(response.status_code, 400)

    def test_non_admin_cannot_patch(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.tenant_token.key}')
        response = self.client.patch(
            f'/api/monitoring/alerts/{self.alert.pk}/',
            {'status': 'acknowledged'},
            format='json',
        )
        self.assertEqual(response.status_code, 403)

    def test_404_on_missing_alert(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.admin_token.key}')
        response = self.client.get('/api/monitoring/alerts/9999/')
        self.assertEqual(response.status_code, 404)


class MonitoringDashboardTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = make_admin('admin_db')
        self.admin_token = Token.objects.create(user=self.admin)
        self.tenant = make_user('tenant_db', Role.TENANT)
        self.tenant_token = Token.objects.create(user=self.tenant)

        SystemMetric.objects.create(metric_type='overdue_invoice_count', value=3)
        SystemMetric.objects.create(metric_type='monthly_revenue', value=200000)

    def test_admin_can_access(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.admin_token.key}')
        response = self.client.get('/api/monitoring/dashboard/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('health_status', response.data)
        self.assertIn('active_alert_counts', response.data)
        self.assertIn('latest_metrics', response.data)
        self.assertIn('top_active_alerts', response.data)
        self.assertIn('trends', response.data)

    def test_non_admin_forbidden(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.tenant_token.key}')
        response = self.client.get('/api/monitoring/dashboard/')
        self.assertEqual(response.status_code, 403)

    def test_health_status_healthy_with_no_alerts(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.admin_token.key}')
        response = self.client.get('/api/monitoring/dashboard/')
        self.assertEqual(response.data['health_status'], 'healthy')

    def test_health_status_warning_with_warning_alert(self):
        rule = make_rule(self.admin, severity='warning')
        AlertInstance.objects.create(rule=rule, triggered_value=15, status='triggered')
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.admin_token.key}')
        response = self.client.get('/api/monitoring/dashboard/')
        self.assertEqual(response.data['health_status'], 'warning')

    def test_health_status_critical_with_critical_alert(self):
        rule = make_rule(self.admin, severity='critical')
        AlertInstance.objects.create(rule=rule, triggered_value=60, status='triggered')
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.admin_token.key}')
        response = self.client.get('/api/monitoring/dashboard/')
        self.assertEqual(response.data['health_status'], 'critical')

    def test_latest_metrics_populated(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.admin_token.key}')
        response = self.client.get('/api/monitoring/dashboard/')
        self.assertIn('overdue_invoice_count', response.data['latest_metrics'])
        self.assertIn('monthly_revenue', response.data['latest_metrics'])

    def test_resolved_alerts_not_in_active_counts(self):
        rule = make_rule(self.admin, severity='critical')
        AlertInstance.objects.create(rule=rule, triggered_value=60, status='resolved')
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.admin_token.key}')
        response = self.client.get('/api/monitoring/dashboard/')
        self.assertEqual(response.data['health_status'], 'healthy')
        self.assertEqual(response.data['active_alert_counts']['critical'], 0)
