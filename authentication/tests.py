from django.urls import reverse
from django.test import override_settings
from unittest.mock import patch
from rest_framework.test import APITestCase
from rest_framework.authtoken.models import Token
from rest_framework import status
from django.contrib.auth import get_user_model
from .models import CustomUser, Role, TenantProfile, LandlordProfile, AgentProfile, NotificationPreference


User = get_user_model()

class RoleAPITests(APITestCase):
    def setUp(self):
        self.role, _ = Role.objects.get_or_create(name="Admin", defaults={"description": "Administrator role"})
        self.user = User.objects.create_user(username="testuser", password="testpass", role=self.role, is_staff=True)
        self.token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')

    def test_role_list_get(self):
        # Seed a non-admin role so the list is non-empty
        Role.objects.get_or_create(name='Tenant')
        url = reverse('role-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = [r['name'] for r in response.data]
        self.assertNotIn('Admin', names)
        self.assertIn('Tenant', names)

    def test_role_list_get_no_auth(self):
        # Registration page calls this unauthenticated — must work
        self.client.credentials()
        Role.objects.get_or_create(name='Landlord')
        response = self.client.get(reverse('role-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = [r['name'] for r in response.data]
        self.assertNotIn('Admin', names)

    def test_role_list_post(self):
        url = reverse('role-list')
        data = {"name": "Editor", "description": "Editor role"}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], "Editor")

    def test_role_list_post_invalid_data(self):
        url = reverse('role-list')
        # Missing required 'name' field
        data = {"description": "Missing name"}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('name', response.data)

    def test_role_detail_get(self):
        url = reverse('role-detail', args=[self.role.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], "Admin")

    def test_role_detail_put(self):
        url = reverse('role-detail', args=[self.role.id])
        data = {"name": "SuperAdmin"}
        response = self.client.put(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], "SuperAdmin")

    def test_role_detail_delete(self):
        url = reverse('role-detail', args=[self.role.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Role.objects.filter(id=self.role.id).exists())

    def test_role_detail_delete_nonexistent(self):
        non_existent_id = self.role.id + 9999
        url = reverse('role-detail', args=[non_existent_id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class RegistrationTestCase(APITestCase):
    def setUp(self):
        self.role, _ = Role.objects.get_or_create(name="Tenant", defaults={"description": "Test role"})

    # Python 3.14 broke super().__copy__() in Django 4.2's BaseContext, which the test
    # client triggers whenever allauth renders a template (email confirm or login message).
    # Mocking add_message prevents all allauth template rendering during this test.
    @override_settings(ACCOUNT_EMAIL_VERIFICATION='none')
    @patch('allauth.account.adapter.DefaultAccountAdapter.add_message')
    def test_register_user_with_phone_and_role(self, _mock_msg):
        url = reverse('rest_register')
        data = {
            "first_name": "Test",
            "last_name": "User",
            "username": "testuser1",
            "email": "testuser1@example.com",
            "password1": "StrongPass!123",
            "password2": "StrongPass!123",
            "phone": "0123456789",
            "role": self.role.id
        }
        response = self.client.post(url, data, format='json')
        # dj-rest-auth returns 204 (no token) when EMAIL_VERIFICATION is 'optional' (default)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        user = CustomUser.objects.get(username="testuser1")
        self.assertEqual(user.phone, "0123456789")
        self.assertEqual(user.role, self.role)
        self.assertEqual(user.first_name, "Test")
        self.assertEqual(user.last_name, "User")


class TenantProfileAPITests(APITestCase):
    def setUp(self):
        self.role, _ = Role.objects.get_or_create(name="Tenant", defaults={"description": "Tenant role"})
        self.user = User.objects.create_user(username="tenant1", password="testpass", role=self.role, is_staff=True)
        self.token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')
        self.profile = TenantProfile.objects.create(
            user=self.user,
            national_id="ID123",
            emergency_contact_name="Jane Doe",
            emergency_contact_phone="0700000000",
        )

    def test_list(self):
        response = self.client.get(reverse('tenant-profile-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_create(self):
        other_user = User.objects.create_user(username="tenant2", password="testpass", role=self.role)
        data = {"user": other_user.id, "national_id": "ID456", "emergency_contact_name": "Bob"}
        response = self.client.post(reverse('tenant-profile-list'), data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['national_id'], "ID456")

    def test_retrieve(self):
        response = self.client.get(reverse('tenant-profile-detail', args=[self.profile.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['national_id'], "ID123")

    def test_update(self):
        response = self.client.put(
            reverse('tenant-profile-detail', args=[self.profile.id]),
            {"national_id": "ID999"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['national_id'], "ID999")

    def test_delete(self):
        response = self.client.delete(reverse('tenant-profile-detail', args=[self.profile.id]))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(TenantProfile.objects.filter(id=self.profile.id).exists())

    def test_retrieve_nonexistent(self):
        response = self.client.get(reverse('tenant-profile-detail', args=[self.profile.id + 9999]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class LandlordProfileAPITests(APITestCase):
    def setUp(self):
        self.role, _ = Role.objects.get_or_create(name="Landlord", defaults={"description": "Landlord role"})
        self.user = User.objects.create_user(username="landlord1", password="testpass", role=self.role, is_staff=True)
        self.token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')
        self.profile = LandlordProfile.objects.create(
            user=self.user,
            company_name="Bett Properties",
            tax_id="TAX001",
            verified=False,
        )

    def test_list(self):
        response = self.client.get(reverse('landlord-profile-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_create(self):
        other_user = User.objects.create_user(username="landlord2", password="testpass", role=self.role)
        data = {"user": other_user.id, "company_name": "Other Co", "tax_id": "TAX002"}
        response = self.client.post(reverse('landlord-profile-list'), data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['company_name'], "Other Co")

    def test_retrieve(self):
        response = self.client.get(reverse('landlord-profile-detail', args=[self.profile.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['company_name'], "Bett Properties")

    def test_update(self):
        response = self.client.put(
            reverse('landlord-profile-detail', args=[self.profile.id]),
            {"verified": True}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['verified'])

    def test_delete(self):
        response = self.client.delete(reverse('landlord-profile-detail', args=[self.profile.id]))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(LandlordProfile.objects.filter(id=self.profile.id).exists())

    def test_retrieve_nonexistent(self):
        response = self.client.get(reverse('landlord-profile-detail', args=[self.profile.id + 9999]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class AgentProfileAPITests(APITestCase):
    def setUp(self):
        self.role, _ = Role.objects.get_or_create(name="Agent", defaults={"description": "Agent role"})
        self.user = User.objects.create_user(username="agent1", password="testpass", role=self.role, is_staff=True)
        self.token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')
        self.profile = AgentProfile.objects.create(
            user=self.user,
            agency_name="Top Agents Ltd",
            license_number="LIC001",
            commission_rate="5.00",
        )

    def test_list(self):
        response = self.client.get(reverse('agent-profile-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_create(self):
        other_user = User.objects.create_user(username="agent2", password="testpass", role=self.role)
        data = {"user": other_user.id, "agency_name": "Fast Agents", "license_number": "LIC002", "commission_rate": "3.50"}
        response = self.client.post(reverse('agent-profile-list'), data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['agency_name'], "Fast Agents")

    def test_retrieve(self):
        response = self.client.get(reverse('agent-profile-detail', args=[self.profile.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['agency_name'], "Top Agents Ltd")

    def test_update(self):
        response = self.client.put(
            reverse('agent-profile-detail', args=[self.profile.id]),
            {"commission_rate": "7.00"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['commission_rate'], "7.00")

    def test_delete(self):
        response = self.client.delete(reverse('agent-profile-detail', args=[self.profile.id]))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(AgentProfile.objects.filter(id=self.profile.id).exists())

    def test_retrieve_nonexistent(self):
        response = self.client.get(reverse('agent-profile-detail', args=[self.profile.id + 9999]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


def make_user(username, role_name):
    role, _ = Role.objects.get_or_create(name=role_name)
    user = User.objects.create_user(username=username, password='testpass', role=role)
    token = Token.objects.create(user=user)
    return user, token


class MeAccountTests(APITestCase):
    def setUp(self):
        self.user, self.token = make_user('meuser', 'Tenant')
        self.user.first_name = 'Alice'
        self.user.last_name = 'Smith'
        self.user.phone = '0700000000'
        self.user.save()
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')

    def test_get_account(self):
        response = self.client.get(reverse('me-account'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], 'meuser')
        self.assertEqual(response.data['first_name'], 'Alice')
        self.assertEqual(response.data['phone'], '0700000000')

    def test_update_account_name_and_phone(self):
        response = self.client.patch(reverse('me-account'), {
            'first_name': 'Bob',
            'last_name': 'Jones',
            'phone': '0711111111',
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['first_name'], 'Bob')
        self.assertEqual(response.data['phone'], '0711111111')
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Bob')

    def test_update_account_email(self):
        response = self.client.patch(reverse('me-account'), {'email': 'newemail@example.com'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], 'newemail@example.com')

    def test_role_is_read_only(self):
        other_role, _ = Role.objects.get_or_create(name='Admin')
        response = self.client.patch(reverse('me-account'), {'role': other_role.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.role.name, 'Tenant')

    def test_unauthenticated_returns_401(self):
        self.client.credentials()
        response = self.client.get(reverse('me-account'))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class MeProfileTests(APITestCase):
    def setUp(self):
        self.tenant_user, self.tenant_token = make_user('tenantme', 'Tenant')
        self.landlord_user, self.landlord_token = make_user('landlordme', 'Landlord')
        self.admin_user, self.admin_token = make_user('adminme', 'Admin')

    def test_tenant_get_profile_auto_creates(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.tenant_token.key}')
        response = self.client.get(reverse('me-profile'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('national_id', response.data)

    def test_tenant_update_profile(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.tenant_token.key}')
        response = self.client.patch(reverse('me-profile'), {
            'national_id': 'NAT123',
            'emergency_contact_name': 'Jane',
            'emergency_contact_phone': '0722000000',
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['national_id'], 'NAT123')

    def test_landlord_get_profile(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.landlord_token.key}')
        response = self.client.get(reverse('me-profile'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('company_name', response.data)

    def test_landlord_update_profile(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.landlord_token.key}')
        response = self.client.patch(reverse('me-profile'), {'company_name': 'My Properties Ltd'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['company_name'], 'My Properties Ltd')

    def test_admin_has_no_role_profile(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.admin_token.key}')
        response = self.client.get(reverse('me-profile'))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class MeNotificationsTests(APITestCase):
    def setUp(self):
        self.user, self.token = make_user('notifuser', 'Tenant')
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')

    def test_get_creates_defaults(self):
        response = self.client.get(reverse('me-notifications'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['email_notifications'])
        self.assertTrue(response.data['payment_due_reminder'])
        self.assertTrue(response.data['lease_expiry_notice'])

    def test_update_preferences(self):
        response = self.client.patch(reverse('me-notifications'), {
            'payment_received': False,
            'new_maintenance_request': False,
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['payment_received'])
        self.assertFalse(response.data['new_maintenance_request'])
        # unchanged fields stay True
        self.assertTrue(response.data['email_notifications'])

    def test_disable_all_emails(self):
        response = self.client.patch(reverse('me-notifications'), {'email_notifications': False})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['email_notifications'])
        prefs = NotificationPreference.objects.get(user=self.user)
        self.assertFalse(prefs.email_notifications)

    def test_idempotent_get(self):
        self.client.get(reverse('me-notifications'))
        self.client.get(reverse('me-notifications'))
        self.assertEqual(NotificationPreference.objects.filter(user=self.user).count(), 1)

    def test_unauthenticated_returns_401(self):
        self.client.credentials()
        response = self.client.get(reverse('me-notifications'))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
