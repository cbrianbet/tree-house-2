from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework.authtoken.models import Token
from rest_framework import status
from django.contrib.auth import get_user_model
from .models import CustomUser, Role


User = get_user_model()

class RoleAPITests(APITestCase):
    def setUp(self):
        self.role = Role.objects.create(name="Admin", description="Administrator role")
        self.user = User.objects.create_user(username="testuser", password="testpass", role=self.role)
        self.token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)

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
