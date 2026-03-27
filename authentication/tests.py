from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework.authtoken.models import Token
from rest_framework import status
from django.contrib.auth import get_user_model
from .models import CustomUser, Role, TenantProfile, LandlordProfile, AgentProfile


User = get_user_model()

class RoleAPITests(APITestCase):
    def setUp(self):
        self.role = Role.objects.create(name="Admin", description="Administrator role")
        self.user = User.objects.create_user(username="testuser", password="testpass", role=self.role)
        self.token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')

    def test_role_list_get(self):
        url = reverse('role-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(any(r['name'] == "Admin" for r in response.data))

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
        self.role = Role.objects.create(name="Tenant", description="Test role")

    def test_register_user_with_phone_and_role(self):
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
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        user = CustomUser.objects.get(username="testuser1")
        self.assertEqual(user.phone, "0123456789")
        self.assertEqual(user.role, self.role)
        self.assertEqual(user.first_name, "Test")
        self.assertEqual(user.last_name, "User")


class TenantProfileAPITests(APITestCase):
    def setUp(self):
        self.role = Role.objects.create(name="Tenant", description="Tenant role")
        self.user = User.objects.create_user(username="tenant1", password="testpass", role=self.role)
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
        self.role = Role.objects.create(name="Landlord", description="Landlord role")
        self.user = User.objects.create_user(username="landlord1", password="testpass", role=self.role)
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
        self.role = Role.objects.create(name="Agent", description="Agent role")
        self.user = User.objects.create_user(username="agent1", password="testpass", role=self.role)
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
