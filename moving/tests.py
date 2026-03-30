from django.test import TestCase
from rest_framework.test import APIClient
from authentication.models import CustomUser, Role, MovingCompanyProfile
from moving.models import MovingBooking, MovingCompanyReview


def make_user(username, role_name):
    role, _ = Role.objects.get_or_create(name=role_name)
    user = CustomUser.objects.create_user(username=username, password='pass', role=role)
    return user


class MovingCompanyDirectoryTests(TestCase):
    def setUp(self):
        self.tenant = make_user('tenant1', Role.TENANT)
        self.company_user = make_user('mover1', Role.MOVING_COMPANY)
        self.company = MovingCompanyProfile.objects.create(
            user=self.company_user,
            company_name='Swift Movers',
            city='Nairobi',
            base_price=5000,
            price_per_km=50,
            is_active=True,
        )
        self.client = APIClient()

    def test_list_companies_authenticated(self):
        self.client.force_authenticate(self.tenant)
        res = self.client.get('/api/moving/companies/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['company_name'], 'Swift Movers')

    def test_list_companies_unauthenticated(self):
        res = self.client.get('/api/moving/companies/')
        self.assertEqual(res.status_code, 401)

    def test_company_detail(self):
        self.client.force_authenticate(self.tenant)
        res = self.client.get(f'/api/moving/companies/{self.company.pk}/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['company_name'], 'Swift Movers')

    def test_company_detail_404(self):
        self.client.force_authenticate(self.tenant)
        res = self.client.get('/api/moving/companies/9999/')
        self.assertEqual(res.status_code, 404)

    def test_inactive_company_not_listed(self):
        self.company.is_active = False
        self.company.save()
        self.client.force_authenticate(self.tenant)
        res = self.client.get('/api/moving/companies/')
        self.assertEqual(len(res.data), 0)


class MovingBookingTests(TestCase):
    def setUp(self):
        self.tenant = make_user('tenant2', Role.TENANT)
        self.company_user = make_user('mover2', Role.MOVING_COMPANY)
        self.other_tenant = make_user('tenant3', Role.TENANT)
        self.company = MovingCompanyProfile.objects.create(
            user=self.company_user,
            company_name='Fast Movers',
            base_price=4000,
            price_per_km=40,
        )
        self.client = APIClient()

    def _create_booking(self, user=None):
        client = APIClient()
        client.force_authenticate(user or self.tenant)
        return client.post('/api/moving/bookings/', {
            'company': self.company.pk,
            'moving_date': '2026-05-01',
            'moving_time': '09:00:00',
            'pickup_address': '1 Old Rd',
            'delivery_address': '2 New Ave',
        }, format='json')

    def test_create_booking(self):
        res = self._create_booking()
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data['status'], 'pending')

    def test_list_bookings_as_customer(self):
        self._create_booking()
        self.client.force_authenticate(self.tenant)
        res = self.client.get('/api/moving/bookings/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.data), 1)

    def test_list_bookings_as_company(self):
        self._create_booking()
        self.client.force_authenticate(self.company_user)
        res = self.client.get('/api/moving/bookings/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.data), 1)

    def test_other_tenant_cannot_see_booking(self):
        self._create_booking()
        self.client.force_authenticate(self.other_tenant)
        res = self.client.get('/api/moving/bookings/')
        self.assertEqual(len(res.data), 0)

    def test_company_confirms_booking(self):
        res = self._create_booking()
        booking_id = res.data['id']
        self.client.force_authenticate(self.company_user)
        res = self.client.put(f'/api/moving/bookings/{booking_id}/', {'status': 'confirmed', 'estimated_price': '6000.00'}, format='json')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['status'], 'confirmed')

    def test_customer_cannot_confirm_booking(self):
        res = self._create_booking()
        booking_id = res.data['id']
        self.client.force_authenticate(self.tenant)
        res = self.client.put(f'/api/moving/bookings/{booking_id}/', {'status': 'confirmed'}, format='json')
        self.assertEqual(res.status_code, 400)

    def test_customer_can_cancel_pending_booking(self):
        res = self._create_booking()
        booking_id = res.data['id']
        self.client.force_authenticate(self.tenant)
        res = self.client.put(f'/api/moving/bookings/{booking_id}/', {'status': 'cancelled'}, format='json')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['status'], 'cancelled')

    def test_unrelated_user_cannot_access_booking(self):
        res = self._create_booking()
        booking_id = res.data['id']
        self.client.force_authenticate(self.other_tenant)
        res = self.client.get(f'/api/moving/bookings/{booking_id}/')
        self.assertEqual(res.status_code, 403)

    def test_booking_detail_404(self):
        self.client.force_authenticate(self.tenant)
        res = self.client.get('/api/moving/bookings/9999/')
        self.assertEqual(res.status_code, 404)


class MovingCompanyReviewTests(TestCase):
    def setUp(self):
        self.tenant = make_user('tenant4', Role.TENANT)
        self.tenant2 = make_user('tenant5', Role.TENANT)
        self.admin_role, _ = Role.objects.get_or_create(name=Role.ADMIN)
        self.admin = CustomUser.objects.create_user(username='admin1', password='pass', role=self.admin_role, is_staff=True)
        self.company_user = make_user('mover3', Role.MOVING_COMPANY)
        self.company = MovingCompanyProfile.objects.create(
            user=self.company_user,
            company_name='Pro Movers',
            base_price=7000,
            price_per_km=60,
        )
        self.client = APIClient()

    def _url(self, review_pk=None):
        base = f'/api/moving/companies/{self.company.pk}/reviews/'
        return base if review_pk is None else f'{base}{review_pk}/'

    def test_add_review(self):
        self.client.force_authenticate(self.tenant)
        res = self.client.post(self._url(), {'rating': 5, 'comment': 'Great service!'}, format='json')
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data['rating'], 5)

    def test_duplicate_review_rejected(self):
        self.client.force_authenticate(self.tenant)
        self.client.post(self._url(), {'rating': 5}, format='json')
        res = self.client.post(self._url(), {'rating': 3}, format='json')
        self.assertEqual(res.status_code, 400)

    def test_invalid_rating(self):
        self.client.force_authenticate(self.tenant)
        res = self.client.post(self._url(), {'rating': 6}, format='json')
        self.assertEqual(res.status_code, 400)

    def test_list_reviews(self):
        MovingCompanyReview.objects.create(company=self.company, reviewer=self.tenant, rating=4)
        self.client.force_authenticate(self.tenant2)
        res = self.client.get(self._url())
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.data), 1)

    def test_update_own_review(self):
        review = MovingCompanyReview.objects.create(company=self.company, reviewer=self.tenant, rating=3)
        self.client.force_authenticate(self.tenant)
        res = self.client.patch(self._url(review.pk), {'rating': 5}, format='json')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['rating'], 5)

    def test_other_user_cannot_update_review(self):
        review = MovingCompanyReview.objects.create(company=self.company, reviewer=self.tenant, rating=3)
        self.client.force_authenticate(self.tenant2)
        res = self.client.patch(self._url(review.pk), {'rating': 1}, format='json')
        self.assertEqual(res.status_code, 403)

    def test_delete_own_review(self):
        review = MovingCompanyReview.objects.create(company=self.company, reviewer=self.tenant, rating=4)
        self.client.force_authenticate(self.tenant)
        res = self.client.delete(self._url(review.pk))
        self.assertEqual(res.status_code, 204)

    def test_admin_can_delete_any_review(self):
        review = MovingCompanyReview.objects.create(company=self.company, reviewer=self.tenant, rating=4)
        self.client.force_authenticate(self.admin)
        res = self.client.delete(self._url(review.pk))
        self.assertEqual(res.status_code, 204)

    def test_review_404(self):
        self.client.force_authenticate(self.tenant)
        res = self.client.get(self._url(9999))
        self.assertEqual(res.status_code, 404)

    def test_company_not_found(self):
        self.client.force_authenticate(self.tenant)
        res = self.client.get('/api/moving/companies/9999/reviews/')
        self.assertEqual(res.status_code, 404)
