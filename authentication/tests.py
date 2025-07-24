from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from .models import CustomUser, Role

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
