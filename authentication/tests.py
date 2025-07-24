from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from .models import CustomUser, Role

class RegistrationTestCase(APITestCase):
    def setUp(self):
        self.role = Role.objects.create(name="Tenant", description="Test role")

    def test_register_user_with_phone_and_role(self):
        url = reverse('dj-rest-auth:registration')  # Adjust if your url name is different
        data = {
            "first_name": "brian",
            "last_name": "bett",
            "username": "brian",
            "email": "cbrian@test.com",
            "password1": "Kaka@10139",
            "password2": "Kaka@10139",
            "phone": "08875569",
            "role": self.role.id
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = CustomUser.objects.get(username="brian")
        self.assertEqual(user.phone, "08875569")
        self.assertEqual(user.role, self.role)
        self.assertEqual(user.first_name, "brian")
        self.assertEqual(user.last_name, "bett")

# Create your tests here.
