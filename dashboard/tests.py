from datetime import date, timedelta
from django.test import TestCase
from rest_framework.test import APIClient
from authentication.models import CustomUser, Role, MovingCompanyProfile, ArtisanProfile
from billing.models import BillingConfig
from property.models import Property, Unit, PropertyAgent, Lease, PropertyReview, TenantReview
from moving.models import MovingBooking
from dashboard.models import RoleChangeLog


def make_user(username, role_name, is_staff=False):
    role, _ = Role.objects.get_or_create(name=role_name)
    user = CustomUser.objects.create_user(username=username, password='pass', role=role, is_staff=is_staff)
    return user


def make_property(owner):
    return Property.objects.create(
        name='Test Property', property_type='apartment', owner=owner, created_by=owner
    )


class AdminOverviewTests(TestCase):
    def setUp(self):
        self.admin = make_user('admin1', Role.ADMIN, is_staff=True)
        self.tenant = make_user('tenant1', Role.TENANT)
        self.client = APIClient()

    def test_admin_can_access(self):
        self.client.force_authenticate(self.admin)
        res = self.client.get('/api/dashboard/admin/')
        self.assertEqual(res.status_code, 200)
        self.assertIn('users', res.data)
        self.assertIn('properties', res.data)
        self.assertIn('billing', res.data)
        self.assertIn('maintenance', res.data)
        self.assertIn('disputes', res.data)
        self.assertIn('moving', res.data)

    def test_non_admin_forbidden(self):
        self.client.force_authenticate(self.tenant)
        res = self.client.get('/api/dashboard/admin/')
        self.assertEqual(res.status_code, 403)

    def test_unauthenticated_denied(self):
        res = self.client.get('/api/dashboard/admin/')
        self.assertEqual(res.status_code, 401)

    def test_user_counts_by_role(self):
        self.client.force_authenticate(self.admin)
        res = self.client.get('/api/dashboard/admin/')
        self.assertIn('Tenant', res.data['users']['by_role'])
        self.assertEqual(res.data['users']['by_role']['Tenant'], 1)


class AdminUserManagementTests(TestCase):
    def setUp(self):
        self.admin = make_user('admin1', Role.ADMIN, is_staff=True)
        self.tenant = make_user('tenant1', Role.TENANT)
        self.landlord = make_user('landlord1', Role.LANDLORD)
        self.client = APIClient()

    def test_list_users(self):
        self.client.force_authenticate(self.admin)
        res = self.client.get('/api/dashboard/admin/users/')
        self.assertEqual(res.status_code, 200)
        self.assertGreaterEqual(len(res.data), 2)

    def test_filter_by_role(self):
        self.client.force_authenticate(self.admin)
        res = self.client.get('/api/dashboard/admin/users/?role=Tenant')
        self.assertEqual(res.status_code, 200)
        self.assertTrue(all(u['role_name'] == 'Tenant' for u in res.data))

    def test_search_by_username(self):
        self.client.force_authenticate(self.admin)
        res = self.client.get('/api/dashboard/admin/users/?search=landlord')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['username'], 'landlord1')

    def test_non_admin_cannot_list(self):
        self.client.force_authenticate(self.tenant)
        res = self.client.get('/api/dashboard/admin/users/')
        self.assertEqual(res.status_code, 403)

    def test_get_user_detail(self):
        self.client.force_authenticate(self.admin)
        res = self.client.get(f'/api/dashboard/admin/users/{self.tenant.pk}/')
        self.assertEqual(res.status_code, 200)
        self.assertIn('user', res.data)
        self.assertIn('role_change_history', res.data)

    def test_user_detail_404(self):
        self.client.force_authenticate(self.admin)
        res = self.client.get('/api/dashboard/admin/users/9999/')
        self.assertEqual(res.status_code, 404)

    def test_change_role_logs_change(self):
        landlord_role, _ = Role.objects.get_or_create(name=Role.LANDLORD)
        self.client.force_authenticate(self.admin)
        res = self.client.put(
            f'/api/dashboard/admin/users/{self.tenant.pk}/',
            {'role': landlord_role.pk, 'reason': 'Upgraded by admin'},
            format='json',
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['role_name'], Role.LANDLORD)
        log = RoleChangeLog.objects.get(user=self.tenant)
        self.assertEqual(log.old_role.name, Role.TENANT)
        self.assertEqual(log.new_role.name, Role.LANDLORD)
        self.assertEqual(log.reason, 'Upgraded by admin')
        self.assertEqual(log.changed_by, self.admin)

    def test_deactivate_user(self):
        self.client.force_authenticate(self.admin)
        res = self.client.put(
            f'/api/dashboard/admin/users/{self.tenant.pk}/',
            {'is_active': False},
            format='json',
        )
        self.assertEqual(res.status_code, 200)
        self.tenant.refresh_from_db()
        self.assertFalse(self.tenant.is_active)

    def test_same_role_does_not_log(self):
        tenant_role, _ = Role.objects.get_or_create(name=Role.TENANT)
        self.client.force_authenticate(self.admin)
        self.client.put(
            f'/api/dashboard/admin/users/{self.tenant.pk}/',
            {'role': tenant_role.pk},
            format='json',
        )
        self.assertEqual(RoleChangeLog.objects.filter(user=self.tenant).count(), 0)


class AdminModerationTests(TestCase):
    def setUp(self):
        self.admin = make_user('admin1', Role.ADMIN, is_staff=True)
        self.landlord = make_user('landlord1', Role.LANDLORD)
        self.tenant = make_user('tenant1', Role.TENANT)
        self.prop = make_property(self.landlord)
        self.client = APIClient()

    def test_list_all_reviews(self):
        PropertyReview.objects.create(reviewer=self.tenant, property=self.prop, rating=4)
        self.client.force_authenticate(self.admin)
        res = self.client.get('/api/dashboard/admin/moderation/reviews/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['type'], 'property')

    def test_filter_by_type_tenant(self):
        PropertyReview.objects.create(reviewer=self.tenant, property=self.prop, rating=4)
        TenantReview.objects.create(reviewer=self.landlord, tenant=self.tenant, property=self.prop, rating=5)
        self.client.force_authenticate(self.admin)
        res = self.client.get('/api/dashboard/admin/moderation/reviews/?type=tenant')
        self.assertEqual(res.status_code, 200)
        self.assertTrue(all(r['type'] == 'tenant' for r in res.data))

    def test_non_admin_forbidden(self):
        self.client.force_authenticate(self.tenant)
        res = self.client.get('/api/dashboard/admin/moderation/reviews/')
        self.assertEqual(res.status_code, 403)

    def test_delete_property_review(self):
        review = PropertyReview.objects.create(reviewer=self.tenant, property=self.prop, rating=3)
        self.client.force_authenticate(self.admin)
        res = self.client.delete(f'/api/dashboard/admin/moderation/reviews/{review.pk}/?type=property')
        self.assertEqual(res.status_code, 204)
        self.assertFalse(PropertyReview.objects.filter(pk=review.pk).exists())

    def test_delete_tenant_review(self):
        review = TenantReview.objects.create(reviewer=self.landlord, tenant=self.tenant, property=self.prop, rating=5)
        self.client.force_authenticate(self.admin)
        res = self.client.delete(f'/api/dashboard/admin/moderation/reviews/{review.pk}/?type=tenant')
        self.assertEqual(res.status_code, 204)

    def test_delete_without_type_returns_400(self):
        review = PropertyReview.objects.create(reviewer=self.tenant, property=self.prop, rating=3)
        self.client.force_authenticate(self.admin)
        res = self.client.delete(f'/api/dashboard/admin/moderation/reviews/{review.pk}/')
        self.assertEqual(res.status_code, 400)

    def test_delete_review_404(self):
        self.client.force_authenticate(self.admin)
        res = self.client.delete('/api/dashboard/admin/moderation/reviews/9999/?type=property')
        self.assertEqual(res.status_code, 404)


class TenantDashboardTests(TestCase):
    def setUp(self):
        self.landlord = make_user('landlord1', Role.LANDLORD)
        self.tenant = make_user('tenant1', Role.TENANT)
        self.other_tenant = make_user('tenant2', Role.TENANT)
        self.prop = make_property(self.landlord)
        self.unit = Unit.objects.create(
            property=self.prop, name='A1', is_occupied=True,
            price='25000.00', created_by=self.landlord
        )
        self.lease = Lease.objects.create(
            unit=self.unit, tenant=self.tenant,
            start_date=date.today(), end_date=date.today() + timedelta(days=180),
            rent_amount='25000.00', is_active=True,
        )
        self.client = APIClient()

    def test_tenant_can_access(self):
        self.client.force_authenticate(self.tenant)
        res = self.client.get('/api/dashboard/tenant/')
        self.assertEqual(res.status_code, 200)
        self.assertIn('active_lease', res.data)
        self.assertIn('invoices', res.data)
        self.assertIn('maintenance', res.data)
        self.assertIn('notifications', res.data)

    def test_active_lease_shown(self):
        self.client.force_authenticate(self.tenant)
        res = self.client.get('/api/dashboard/tenant/')
        self.assertIsNotNone(res.data['active_lease'])
        self.assertEqual(res.data['active_lease']['unit'], 'A1')

    def test_active_lease_includes_extended_lease_unit_property_landlord(self):
        self.landlord.first_name = 'James'
        self.landlord.last_name = 'Bett'
        self.landlord.phone = '+254700111222'
        self.landlord.email = 'james@example.com'
        self.landlord.save()
        self.unit.floor = '4'
        self.unit.bedrooms = 2
        self.unit.bathrooms = 1
        self.unit.service_charge = '2500.00'
        self.unit.security_deposit = '50000.00'
        self.unit.parking_space = True
        self.unit.parking_slots = 1
        self.unit.amenities = 'Balcony'
        self.unit.save()
        self.prop.description = '14 Westlands Road\nSecond line'
        self.prop.save()

        self.client.force_authenticate(self.tenant)
        res = self.client.get('/api/dashboard/tenant/')
        al = res.data['active_lease']
        self.assertEqual(al['id'], self.lease.id)
        self.assertEqual(al['unit_id'], self.unit.id)
        self.assertEqual(al['property_id'], self.prop.id)
        self.assertEqual(al['unit_name'], 'A1')
        self.assertTrue(al['is_active'])
        self.assertEqual(al['unit_detail']['floor'], '4')
        self.assertEqual(al['unit_detail']['bedrooms'], 2)
        self.assertEqual(al['unit_detail']['service_charge'], '2500.00')
        self.assertEqual(al['unit_detail']['security_deposit'], '50000.00')
        self.assertEqual(al['unit_detail']['parking_slots'], 1)
        self.assertEqual(al['property_detail']['name'], 'Test Property')
        self.assertEqual(al['property_detail']['location_summary'], '14 Westlands Road')
        self.assertEqual(al['landlord']['user_id'], self.landlord.id)
        self.assertEqual(al['landlord']['first_name'], 'James')
        self.assertEqual(al['landlord']['phone'], '+254700111222')
        self.assertEqual(al['landlord']['email'], 'james@example.com')
        self.assertIsNone(al['billing'])

    def test_active_lease_billing_snapshot_when_configured(self):
        BillingConfig.objects.create(
            property=self.prop,
            rent_due_day=1,
            grace_period_days=3,
            late_fee_percentage='5.00',
            late_fee_mode=BillingConfig.LATE_FEE_MODE_PERCENTAGE,
            updated_by=self.landlord,
        )
        self.client.force_authenticate(self.tenant)
        res = self.client.get('/api/dashboard/tenant/')
        bill = res.data['active_lease']['billing']
        self.assertIsNotNone(bill)
        self.assertEqual(bill['rent_due_day'], 1)
        self.assertEqual(bill['grace_period_days'], 3)
        self.assertEqual(bill['late_fee_percentage'], '5.00')
        self.assertEqual(bill['late_fee_mode'], 'percentage')
        self.assertIsNone(bill['late_fee_fixed_amount'])

    def test_non_tenant_forbidden(self):
        self.client.force_authenticate(self.landlord)
        res = self.client.get('/api/dashboard/tenant/')
        self.assertEqual(res.status_code, 403)

    def test_no_active_lease(self):
        self.client.force_authenticate(self.other_tenant)
        res = self.client.get('/api/dashboard/tenant/')
        self.assertEqual(res.status_code, 200)
        self.assertIsNone(res.data['active_lease'])


class ArtisanDashboardTests(TestCase):
    def setUp(self):
        self.artisan = make_user('artisan1', Role.ARTISAN)
        ArtisanProfile.objects.create(user=self.artisan, trade='plumbing')
        self.landlord = make_user('landlord1', Role.LANDLORD)
        self.client = APIClient()

    def test_artisan_can_access(self):
        self.client.force_authenticate(self.artisan)
        res = self.client.get('/api/dashboard/artisan/')
        self.assertEqual(res.status_code, 200)
        self.assertIn('open_jobs', res.data)
        self.assertIn('active_bids', res.data)
        self.assertIn('completed_this_month', res.data)
        self.assertEqual(res.data['trade'], 'plumbing')

    def test_non_artisan_forbidden(self):
        self.client.force_authenticate(self.landlord)
        res = self.client.get('/api/dashboard/artisan/')
        self.assertEqual(res.status_code, 403)


class AgentDashboardTests(TestCase):
    def setUp(self):
        self.agent = make_user('agent1', Role.AGENT)
        self.landlord = make_user('landlord1', Role.LANDLORD)
        self.prop = make_property(self.landlord)
        PropertyAgent.objects.create(property=self.prop, agent=self.agent, appointed_by=self.landlord)
        self.client = APIClient()

    def test_agent_can_access(self):
        self.client.force_authenticate(self.agent)
        res = self.client.get('/api/dashboard/agent/')
        self.assertEqual(res.status_code, 200)
        self.assertIn('assigned_properties', res.data)
        self.assertIn('pending_applications', res.data)
        self.assertIn('open_maintenance_requests', res.data)
        self.assertIn('active_disputes', res.data)

    def test_assigned_property_count(self):
        self.client.force_authenticate(self.agent)
        res = self.client.get('/api/dashboard/agent/')
        self.assertEqual(res.data['assigned_properties']['count'], 1)

    def test_non_agent_forbidden(self):
        self.client.force_authenticate(self.landlord)
        res = self.client.get('/api/dashboard/agent/')
        self.assertEqual(res.status_code, 403)


class MovingCompanyDashboardTests(TestCase):
    def setUp(self):
        self.company_user = make_user('mover1', Role.MOVING_COMPANY)
        self.profile = MovingCompanyProfile.objects.create(
            user=self.company_user, company_name='Swift Movers', base_price=5000, price_per_km=50
        )
        self.customer = make_user('customer1', Role.TENANT)
        self.client = APIClient()

    def test_moving_company_can_access(self):
        self.client.force_authenticate(self.company_user)
        res = self.client.get('/api/dashboard/moving-company/')
        self.assertEqual(res.status_code, 200)
        self.assertIn('bookings', res.data)
        self.assertIn('reviews', res.data)
        self.assertEqual(res.data['company_name'], 'Swift Movers')

    def test_bookings_counted_by_status(self):
        MovingBooking.objects.create(
            company=self.profile, customer=self.customer,
            moving_date=date.today() + timedelta(days=5),
            moving_time='09:00:00',
            pickup_address='A', delivery_address='B',
            status='pending',
        )
        self.client.force_authenticate(self.company_user)
        res = self.client.get('/api/dashboard/moving-company/')
        self.assertEqual(res.data['bookings']['pending'], 1)
        self.assertEqual(res.data['bookings']['total'], 1)

    def test_non_moving_company_forbidden(self):
        self.client.force_authenticate(self.customer)
        res = self.client.get('/api/dashboard/moving-company/')
        self.assertEqual(res.status_code, 403)

    def test_no_profile_returns_404(self):
        mover2 = make_user('mover2', Role.MOVING_COMPANY)
        self.client.force_authenticate(mover2)
        res = self.client.get('/api/dashboard/moving-company/')
        self.assertEqual(res.status_code, 404)
