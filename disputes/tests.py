from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token

from authentication.models import CustomUser, Role
from property.models import Property, Unit, Lease, PropertyAgent
from .models import Dispute, DisputeMessage


def make_user(username, role_name):
    role, _ = Role.objects.get_or_create(name=role_name)
    user = CustomUser.objects.create_user(username=username, password='testpass', role=role)
    token = Token.objects.create(user=user)
    return user, token


class DisputeListCreateTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.landlord, self.landlord_token = make_user('landlord1', Role.LANDLORD)
        self.tenant, self.tenant_token = make_user('tenant1', Role.TENANT)
        self.agent, self.agent_token = make_user('agent1', Role.AGENT)
        self.artisan, self.artisan_token = make_user('artisan1', Role.ARTISAN)
        self.admin, self.admin_token = make_user('admin1', Role.ADMIN)
        self.other_landlord, self.other_landlord_token = make_user('landlord2', Role.LANDLORD)

        self.property = Property.objects.create(
            owner=self.landlord,
            name='Test Property',
            property_type='apartment',
            created_by=self.landlord,
        )
        self.unit = Unit.objects.create(
            property=self.property,
            name='Unit 1',
            created_by=self.landlord,
        )
        self.lease = Lease.objects.create(
            unit=self.unit,
            tenant=self.tenant,
            start_date='2024-01-01',
            rent_amount='10000.00',
            is_active=True,
        )

        self.other_property = Property.objects.create(
            owner=self.other_landlord,
            name='Other Property',
            property_type='house',
            created_by=self.other_landlord,
        )
        self.other_unit = Unit.objects.create(
            property=self.other_property,
            name='Unit A',
            created_by=self.other_landlord,
        )

    def _dispute_data(self, prop=None, unit=None):
        prop = prop or self.property
        data = {
            'property': prop.id,
            'dispute_type': 'rent',
            'title': 'Test dispute',
            'description': 'Some description.',
        }
        if unit:
            data['unit'] = unit.id
        return data

    def test_tenant_can_create_dispute(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.tenant_token.key}')
        resp = self.client.post('/api/disputes/', self._dispute_data(), format='json')
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data['dispute_type'], 'rent')
        self.assertEqual(resp.data['status'], 'open')

    def test_tenant_without_lease_cannot_create(self):
        # Create a tenant with no lease
        tenant2, token2 = make_user('tenant_nolease', Role.TENANT)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token2.key}')
        resp = self.client.post('/api/disputes/', self._dispute_data(), format='json')
        self.assertEqual(resp.status_code, 403)

    def test_landlord_can_create_dispute(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.landlord_token.key}')
        resp = self.client.post('/api/disputes/', self._dispute_data(), format='json')
        self.assertEqual(resp.status_code, 201)

    def test_landlord_cannot_create_for_others_property(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.landlord_token.key}')
        resp = self.client.post('/api/disputes/', self._dispute_data(prop=self.other_property), format='json')
        self.assertEqual(resp.status_code, 403)

    def test_agent_cannot_create_dispute(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.agent_token.key}')
        resp = self.client.post('/api/disputes/', self._dispute_data(), format='json')
        self.assertEqual(resp.status_code, 403)

    def test_artisan_cannot_access_disputes(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.artisan_token.key}')
        resp = self.client.get('/api/disputes/')
        self.assertEqual(resp.status_code, 403)

    def test_admin_sees_all_disputes(self):
        # Create disputes by different users
        Dispute.objects.create(
            created_by=self.tenant,
            property=self.property,
            dispute_type='rent',
            title='Tenant dispute',
            description='desc',
        )
        Dispute.objects.create(
            created_by=self.landlord,
            property=self.property,
            dispute_type='noise',
            title='Landlord dispute',
            description='desc',
        )
        Dispute.objects.create(
            created_by=self.other_landlord,
            property=self.other_property,
            dispute_type='deposit',
            title='Other property dispute',
            description='desc',
        )
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.admin_token.key}')
        resp = self.client.get('/api/disputes/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 3)

    def test_tenant_sees_own_disputes_only(self):
        Dispute.objects.create(
            created_by=self.tenant,
            property=self.property,
            dispute_type='rent',
            title='Tenant dispute',
            description='desc',
        )
        Dispute.objects.create(
            created_by=self.landlord,
            property=self.property,
            dispute_type='noise',
            title='Landlord dispute',
            description='desc',
        )
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.tenant_token.key}')
        resp = self.client.get('/api/disputes/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 1)
        self.assertEqual(resp.data[0]['title'], 'Tenant dispute')

    def test_landlord_sees_own_property_disputes(self):
        Dispute.objects.create(
            created_by=self.tenant,
            property=self.property,
            dispute_type='rent',
            title='On landlord property',
            description='desc',
        )
        Dispute.objects.create(
            created_by=self.other_landlord,
            property=self.other_property,
            dispute_type='deposit',
            title='On other property',
            description='desc',
        )
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.landlord_token.key}')
        resp = self.client.get('/api/disputes/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 1)
        self.assertEqual(resp.data[0]['title'], 'On landlord property')


class DisputeDetailTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.landlord, self.landlord_token = make_user('landlord_d', Role.LANDLORD)
        self.tenant, self.tenant_token = make_user('tenant_d', Role.TENANT)
        self.admin, self.admin_token = make_user('admin_d', Role.ADMIN)
        self.unrelated, self.unrelated_token = make_user('unrelated_d', Role.TENANT)

        self.property = Property.objects.create(
            owner=self.landlord,
            name='Detail Property',
            property_type='apartment',
            created_by=self.landlord,
        )
        self.unit = Unit.objects.create(
            property=self.property,
            name='Unit 1',
            created_by=self.landlord,
        )
        self.lease = Lease.objects.create(
            unit=self.unit,
            tenant=self.tenant,
            start_date='2024-01-01',
            rent_amount='10000.00',
            is_active=True,
        )
        self.dispute = Dispute.objects.create(
            created_by=self.tenant,
            property=self.property,
            dispute_type='rent',
            title='Detail test dispute',
            description='Some description.',
        )

    def test_creator_can_retrieve(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.tenant_token.key}')
        resp = self.client.get(f'/api/disputes/{self.dispute.pk}/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['id'], self.dispute.pk)

    def test_property_owner_can_retrieve(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.landlord_token.key}')
        resp = self.client.get(f'/api/disputes/{self.dispute.pk}/')
        self.assertEqual(resp.status_code, 200)

    def test_unrelated_user_cannot_retrieve(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.unrelated_token.key}')
        resp = self.client.get(f'/api/disputes/{self.dispute.pk}/')
        self.assertEqual(resp.status_code, 403)

    def test_nonexistent_returns_404(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.tenant_token.key}')
        resp = self.client.get('/api/disputes/99999/')
        self.assertEqual(resp.status_code, 404)

    def test_creator_can_close(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.tenant_token.key}')
        resp = self.client.patch(f'/api/disputes/{self.dispute.pk}/', {'status': 'closed'}, format='json')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['status'], 'closed')

    def test_landlord_can_move_to_under_review(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.landlord_token.key}')
        resp = self.client.patch(f'/api/disputes/{self.dispute.pk}/', {'status': 'under_review'}, format='json')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['status'], 'under_review')

    def test_tenant_cannot_move_to_under_review(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.tenant_token.key}')
        resp = self.client.patch(f'/api/disputes/{self.dispute.pk}/', {'status': 'under_review'}, format='json')
        self.assertEqual(resp.status_code, 400)

    def test_invalid_transition_returns_400(self):
        # Try to go directly from open to resolved (must be under_review first)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.admin_token.key}')
        resp = self.client.patch(f'/api/disputes/{self.dispute.pk}/', {'status': 'resolved'}, format='json')
        self.assertEqual(resp.status_code, 400)

    def test_admin_can_resolve_after_under_review(self):
        self.dispute.status = 'under_review'
        self.dispute.save()
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.admin_token.key}')
        resp = self.client.patch(f'/api/disputes/{self.dispute.pk}/', {'status': 'resolved'}, format='json')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['status'], 'resolved')
        self.assertIsNotNone(resp.data['resolved_at'])
        self.assertEqual(resp.data['resolved_by'], self.admin.pk)

    def test_resolved_dispute_cannot_be_changed(self):
        self.dispute.status = 'resolved'
        self.dispute.save()
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.admin_token.key}')
        resp = self.client.patch(f'/api/disputes/{self.dispute.pk}/', {'status': 'closed'}, format='json')
        self.assertEqual(resp.status_code, 400)


class DisputeMessageTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.landlord, self.landlord_token = make_user('landlord_m', Role.LANDLORD)
        self.tenant, self.tenant_token = make_user('tenant_m', Role.TENANT)
        self.outsider, self.outsider_token = make_user('outsider_m', Role.TENANT)

        self.property = Property.objects.create(
            owner=self.landlord,
            name='Message Property',
            property_type='apartment',
            created_by=self.landlord,
        )
        self.unit = Unit.objects.create(
            property=self.property,
            name='Unit 1',
            created_by=self.landlord,
        )
        self.lease = Lease.objects.create(
            unit=self.unit,
            tenant=self.tenant,
            start_date='2024-01-01',
            rent_amount='10000.00',
            is_active=True,
        )
        self.dispute = Dispute.objects.create(
            created_by=self.tenant,
            property=self.property,
            dispute_type='maintenance',
            title='Message test dispute',
            description='Some description.',
        )

    def test_participant_can_post_message(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.tenant_token.key}')
        resp = self.client.post(
            f'/api/disputes/{self.dispute.pk}/messages/',
            {'body': 'Hello, this is a message.'},
            format='json',
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data['body'], 'Hello, this is a message.')
        self.assertEqual(resp.data['sender'], self.tenant.pk)

    def test_property_owner_can_post_message(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.landlord_token.key}')
        resp = self.client.post(
            f'/api/disputes/{self.dispute.pk}/messages/',
            {'body': 'Landlord reply.'},
            format='json',
        )
        self.assertEqual(resp.status_code, 201)

    def test_participant_can_list_messages(self):
        DisputeMessage.objects.create(dispute=self.dispute, sender=self.tenant, body='First message.')
        DisputeMessage.objects.create(dispute=self.dispute, sender=self.landlord, body='Second message.')

        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.tenant_token.key}')
        resp = self.client.get(f'/api/disputes/{self.dispute.pk}/messages/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 2)

    def test_non_participant_cannot_post(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.outsider_token.key}')
        resp = self.client.post(
            f'/api/disputes/{self.dispute.pk}/messages/',
            {'body': 'I should not be able to post.'},
            format='json',
        )
        self.assertEqual(resp.status_code, 403)

    def test_non_participant_cannot_list_messages(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.outsider_token.key}')
        resp = self.client.get(f'/api/disputes/{self.dispute.pk}/messages/')
        self.assertEqual(resp.status_code, 403)
