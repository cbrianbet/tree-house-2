from django.test import TestCase
from rest_framework.test import APIClient
from authentication.models import CustomUser, Role
from property.models import Property, PropertyAgent
from neighborhood.models import NeighborhoodInsight


def make_user(username, role_name):
    role, _ = Role.objects.get_or_create(name=role_name)
    user = CustomUser.objects.create_user(username=username, password='pass', role=role)
    return user


def make_property(owner):
    return Property.objects.create(
        name='Test Property',
        property_type='apartment',
        owner=owner,
        created_by=owner,
    )


class NeighborhoodInsightTests(TestCase):
    def setUp(self):
        self.landlord = make_user('landlord1', Role.LANDLORD)
        self.other_landlord = make_user('landlord2', Role.LANDLORD)
        self.agent = make_user('agent1', Role.AGENT)
        self.tenant = make_user('tenant1', Role.TENANT)
        admin_role, _ = Role.objects.get_or_create(name=Role.ADMIN)
        self.admin = CustomUser.objects.create_user(username='admin1', password='pass', role=admin_role, is_staff=True)

        self.prop = make_property(self.landlord)
        PropertyAgent.objects.create(property=self.prop, agent=self.agent, appointed_by=self.landlord)

        self.client = APIClient()

    def _list_url(self):
        return f'/api/neighborhood/properties/{self.prop.pk}/insights/'

    def _detail_url(self, pk):
        return f'/api/neighborhood/properties/{self.prop.pk}/insights/{pk}/'

    def _payload(self, **kwargs):
        data = {
            'insight_type': 'school',
            'name': 'Westlands Primary',
            'address': '1 School Rd',
            'distance_km': '0.5',
        }
        data.update(kwargs)
        return data

    # --- List ---
    def test_any_auth_user_can_list(self):
        self.client.force_authenticate(self.tenant)
        res = self.client.get(self._list_url())
        self.assertEqual(res.status_code, 200)

    def test_unauthenticated_cannot_list(self):
        res = self.client.get(self._list_url())
        self.assertEqual(res.status_code, 401)

    def test_list_404_for_unknown_property(self):
        self.client.force_authenticate(self.tenant)
        res = self.client.get('/api/neighborhood/properties/9999/insights/')
        self.assertEqual(res.status_code, 404)

    def test_filter_by_type(self):
        NeighborhoodInsight.objects.create(
            property=self.prop, insight_type='school', name='School A', added_by=self.landlord
        )
        NeighborhoodInsight.objects.create(
            property=self.prop, insight_type='hospital', name='Hospital B', added_by=self.landlord
        )
        self.client.force_authenticate(self.tenant)
        res = self.client.get(self._list_url() + '?type=school')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['insight_type'], 'school')

    # --- Create ---
    def test_landlord_can_add_insight(self):
        self.client.force_authenticate(self.landlord)
        res = self.client.post(self._list_url(), self._payload(), format='json')
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data['name'], 'Westlands Primary')

    def test_assigned_agent_can_add_insight(self):
        self.client.force_authenticate(self.agent)
        res = self.client.post(self._list_url(), self._payload(), format='json')
        self.assertEqual(res.status_code, 201)

    def test_admin_can_add_insight(self):
        self.client.force_authenticate(self.admin)
        res = self.client.post(self._list_url(), self._payload(), format='json')
        self.assertEqual(res.status_code, 201)

    def test_tenant_cannot_add_insight(self):
        self.client.force_authenticate(self.tenant)
        res = self.client.post(self._list_url(), self._payload(), format='json')
        self.assertEqual(res.status_code, 403)

    def test_other_landlord_cannot_add_insight(self):
        self.client.force_authenticate(self.other_landlord)
        res = self.client.post(self._list_url(), self._payload(), format='json')
        self.assertEqual(res.status_code, 403)

    # --- Detail ---
    def test_get_insight(self):
        insight = NeighborhoodInsight.objects.create(
            property=self.prop, insight_type='hospital', name='City Hospital', added_by=self.landlord
        )
        self.client.force_authenticate(self.tenant)
        res = self.client.get(self._detail_url(insight.pk))
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['name'], 'City Hospital')

    def test_insight_detail_404(self):
        self.client.force_authenticate(self.tenant)
        res = self.client.get(self._detail_url(9999))
        self.assertEqual(res.status_code, 404)

    # --- Update ---
    def test_adder_can_update_insight(self):
        insight = NeighborhoodInsight.objects.create(
            property=self.prop, insight_type='school', name='Old Name', added_by=self.landlord
        )
        self.client.force_authenticate(self.landlord)
        res = self.client.patch(self._detail_url(insight.pk), {'name': 'New Name'}, format='json')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['name'], 'New Name')

    def test_non_adder_cannot_update_insight(self):
        insight = NeighborhoodInsight.objects.create(
            property=self.prop, insight_type='school', name='Old Name', added_by=self.landlord
        )
        self.client.force_authenticate(self.agent)
        res = self.client.patch(self._detail_url(insight.pk), {'name': 'Hacked'}, format='json')
        self.assertEqual(res.status_code, 403)

    def test_admin_can_update_any_insight(self):
        insight = NeighborhoodInsight.objects.create(
            property=self.prop, insight_type='school', name='Old Name', added_by=self.landlord
        )
        self.client.force_authenticate(self.admin)
        res = self.client.patch(self._detail_url(insight.pk), {'notes': 'Admin note'}, format='json')
        self.assertEqual(res.status_code, 200)

    # --- Delete ---
    def test_adder_can_delete_insight(self):
        insight = NeighborhoodInsight.objects.create(
            property=self.prop, insight_type='school', name='To Delete', added_by=self.landlord
        )
        self.client.force_authenticate(self.landlord)
        res = self.client.delete(self._detail_url(insight.pk))
        self.assertEqual(res.status_code, 204)

    def test_non_adder_cannot_delete_insight(self):
        insight = NeighborhoodInsight.objects.create(
            property=self.prop, insight_type='school', name='Protected', added_by=self.landlord
        )
        self.client.force_authenticate(self.tenant)
        res = self.client.delete(self._detail_url(insight.pk))
        self.assertEqual(res.status_code, 403)

    def test_admin_can_delete_any_insight(self):
        insight = NeighborhoodInsight.objects.create(
            property=self.prop, insight_type='transit', name='Bus Stop', added_by=self.landlord
        )
        self.client.force_authenticate(self.admin)
        res = self.client.delete(self._detail_url(insight.pk))
        self.assertEqual(res.status_code, 204)
