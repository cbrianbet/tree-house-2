from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework.authtoken.models import Token
from rest_framework import status
from django.contrib.auth import get_user_model
from authentication.models import Role
from .models import Property, Unit, PropertyAgent

User = get_user_model()


def make_user(username, role_name, password='testpass'):
    role = Role.objects.get_or_create(name=role_name)[0]
    user = User.objects.create_user(username=username, password=password, role=role)
    token = Token.objects.create(user=user)
    return user, token


class PropertyCRUDTests(APITestCase):
    def setUp(self):
        self.landlord, self.landlord_token = make_user('landlord1', 'Landlord')
        self.other_landlord, self.other_token = make_user('landlord2', 'Landlord')
        self.admin, self.admin_token = make_user('admin1', 'Admin')
        self.admin.is_staff = True
        self.admin.save()
        self.tenant, self.tenant_token = make_user('tenant1', 'Tenant')
        self.agent, self.agent_token = make_user('agent1', 'Agent')

        self.property = Property.objects.create(
            name="Sunset Apartments",
            property_type="apartment",
            owner=self.landlord,
            created_by=self.landlord,
        )

    def auth(self, token):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

    # --- List ---
    def test_landlord_sees_own_properties(self):
        self.auth(self.landlord_token)
        response = self.client.get(reverse('property-list-create'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_other_landlord_sees_no_properties(self):
        self.auth(self.other_token)
        response = self.client.get(reverse('property-list-create'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

    def test_admin_sees_all_properties(self):
        self.auth(self.admin_token)
        response = self.client.get(reverse('property-list-create'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_agent_sees_assigned_properties_only(self):
        self.auth(self.agent_token)
        response = self.client.get(reverse('property-list-create'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

        PropertyAgent.objects.create(property=self.property, agent=self.agent, appointed_by=self.landlord)
        response = self.client.get(reverse('property-list-create'))
        self.assertEqual(len(response.data), 1)

    # --- Create ---
    def test_landlord_can_create_property(self):
        self.auth(self.landlord_token)
        data = {"name": "New Place", "property_type": "house"}
        response = self.client.post(reverse('property-list-create'), data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_tenant_cannot_create_property(self):
        self.auth(self.tenant_token)
        data = {"name": "My Place", "property_type": "house"}
        response = self.client.post(reverse('property-list-create'), data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_agent_cannot_create_property(self):
        self.auth(self.agent_token)
        data = {"name": "My Place", "property_type": "house"}
        response = self.client.post(reverse('property-list-create'), data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # --- Retrieve ---
    def test_owner_can_retrieve_property(self):
        self.auth(self.landlord_token)
        response = self.client.get(reverse('property-detail', args=[self.property.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_assigned_agent_can_retrieve_property(self):
        PropertyAgent.objects.create(property=self.property, agent=self.agent, appointed_by=self.landlord)
        self.auth(self.agent_token)
        response = self.client.get(reverse('property-detail', args=[self.property.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_unassigned_agent_cannot_retrieve_property(self):
        self.auth(self.agent_token)
        response = self.client.get(reverse('property-detail', args=[self.property.id]))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # --- Update ---
    def test_owner_can_update_property(self):
        self.auth(self.landlord_token)
        response = self.client.put(reverse('property-detail', args=[self.property.id]), {"name": "Updated"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], "Updated")

    def test_assigned_agent_can_update_property(self):
        PropertyAgent.objects.create(property=self.property, agent=self.agent, appointed_by=self.landlord)
        self.auth(self.agent_token)
        response = self.client.put(reverse('property-detail', args=[self.property.id]), {"name": "Agent Updated"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    # --- Delete ---
    def test_owner_can_delete_property(self):
        self.auth(self.landlord_token)
        response = self.client.delete(reverse('property-detail', args=[self.property.id]))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_agent_cannot_delete_property(self):
        PropertyAgent.objects.create(property=self.property, agent=self.agent, appointed_by=self.landlord)
        self.auth(self.agent_token)
        response = self.client.delete(reverse('property-detail', args=[self.property.id]))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class UnitCRUDTests(APITestCase):
    def setUp(self):
        self.landlord, self.landlord_token = make_user('landlord1', 'Landlord')
        self.agent, self.agent_token = make_user('agent1', 'Agent')
        self.tenant, self.tenant_token = make_user('tenant1', 'Tenant')
        self.admin, self.admin_token = make_user('admin1', 'Admin')
        self.admin.is_staff = True
        self.admin.save()

        self.property = Property.objects.create(
            name="Test Property", property_type="apartment",
            owner=self.landlord, created_by=self.landlord,
        )
        self.unit = Unit.objects.create(
            property=self.property, name="Unit 1",
            price="40000", created_by=self.landlord,
        )

    def auth(self, token):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

    def test_anyone_can_list_units(self):
        self.auth(self.tenant_token)
        response = self.client.get(reverse('unit-list-create', args=[self.property.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_landlord_can_add_unit(self):
        self.auth(self.landlord_token)
        data = {"name": "Unit 2", "price": "45000", "bedrooms": 2}
        response = self.client.post(reverse('unit-list-create', args=[self.property.id]), data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_assigned_agent_can_add_unit(self):
        PropertyAgent.objects.create(property=self.property, agent=self.agent, appointed_by=self.landlord)
        self.auth(self.agent_token)
        data = {"name": "Unit 3", "price": "42000", "bedrooms": 1}
        response = self.client.post(reverse('unit-list-create', args=[self.property.id]), data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_tenant_cannot_add_unit(self):
        self.auth(self.tenant_token)
        data = {"name": "Unit 4", "price": "42000"}
        response = self.client.post(reverse('unit-list-create', args=[self.property.id]), data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_owner_can_update_unit(self):
        self.auth(self.landlord_token)
        response = self.client.put(reverse('unit-detail', args=[self.unit.id]), {"price": "50000"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_assigned_agent_can_update_unit(self):
        PropertyAgent.objects.create(property=self.property, agent=self.agent, appointed_by=self.landlord)
        self.auth(self.agent_token)
        response = self.client.put(reverse('unit-detail', args=[self.unit.id]), {"price": "48000"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_agent_cannot_delete_unit(self):
        PropertyAgent.objects.create(property=self.property, agent=self.agent, appointed_by=self.landlord)
        self.auth(self.agent_token)
        response = self.client.delete(reverse('unit-detail', args=[self.unit.id]))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_owner_can_delete_unit(self):
        self.auth(self.landlord_token)
        response = self.client.delete(reverse('unit-detail', args=[self.unit.id]))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)


class PropertyAgentTests(APITestCase):
    def setUp(self):
        self.landlord, self.landlord_token = make_user('landlord1', 'Landlord')
        self.agent, self.agent_token = make_user('agent1', 'Agent')
        self.other_landlord, self.other_token = make_user('landlord2', 'Landlord')

        self.property = Property.objects.create(
            name="Test Property", property_type="apartment",
            owner=self.landlord, created_by=self.landlord,
        )

    def auth(self, token):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

    def test_landlord_can_appoint_agent(self):
        self.auth(self.landlord_token)
        response = self.client.post(
            reverse('property-agent-list-create', args=[self.property.id]),
            {"agent": self.agent.id}
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(PropertyAgent.objects.filter(property=self.property, agent=self.agent).exists())

    def test_cannot_appoint_same_agent_twice(self):
        PropertyAgent.objects.create(property=self.property, agent=self.agent, appointed_by=self.landlord)
        self.auth(self.landlord_token)
        response = self.client.post(
            reverse('property-agent-list-create', args=[self.property.id]),
            {"agent": self.agent.id}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_other_landlord_cannot_appoint_agent(self):
        self.auth(self.other_token)
        response = self.client.post(
            reverse('property-agent-list-create', args=[self.property.id]),
            {"agent": self.agent.id}
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_landlord_can_list_agents(self):
        PropertyAgent.objects.create(property=self.property, agent=self.agent, appointed_by=self.landlord)
        self.auth(self.landlord_token)
        response = self.client.get(reverse('property-agent-list-create', args=[self.property.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_landlord_can_remove_agent(self):
        PropertyAgent.objects.create(property=self.property, agent=self.agent, appointed_by=self.landlord)
        self.auth(self.landlord_token)
        response = self.client.delete(
            reverse('property-agent-detail', args=[self.property.id, self.agent.id])
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(PropertyAgent.objects.filter(property=self.property, agent=self.agent).exists())

    def test_remove_nonexistent_agent_returns_404(self):
        self.auth(self.landlord_token)
        response = self.client.delete(
            reverse('property-agent-detail', args=[self.property.id, self.agent.id])
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
