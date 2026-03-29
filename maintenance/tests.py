from datetime import date
from decimal import Decimal

from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework.authtoken.models import Token
from rest_framework import status
from django.contrib.auth import get_user_model

from authentication.models import Role, ArtisanProfile
from property.models import Property, Unit, Lease, PropertyAgent
from maintenance.models import MaintenanceRequest, MaintenanceBid, MaintenanceNote

User = get_user_model()


def make_user(username, role_name, is_staff=False):
    role = Role.objects.get_or_create(name=role_name)[0]
    user = User.objects.create_user(username=username, password='testpass', role=role, email=f'{username}@test.com')
    if is_staff:
        user.is_staff = True
        user.save()
    token = Token.objects.create(user=user)
    return user, token


def make_property(owner):
    return Property.objects.create(name='Test Property', property_type='apartment', owner=owner, created_by=owner)


def make_unit(prop, owner):
    return Unit.objects.create(property=prop, name='Unit 1', price='40000', created_by=owner)


def make_lease(unit, tenant):
    return Lease.objects.create(unit=unit, tenant=tenant, start_date=date.today(), rent_amount='40000', is_active=True)


def make_request(prop, submitter, unit=None, category='plumbing', req_status='submitted'):
    return MaintenanceRequest.objects.create(
        property=prop,
        unit=unit,
        submitted_by=submitter,
        title='Leaking tap',
        description='Kitchen tap is leaking.',
        category=category,
        priority='medium',
        status=req_status,
    )


class RequestSubmissionTests(APITestCase):
    def setUp(self):
        self.landlord, self.landlord_token = make_user('landlord1', 'Landlord')
        self.tenant, self.tenant_token = make_user('tenant1', 'Tenant')
        self.agent, self.agent_token = make_user('agent1', 'Agent')
        self.artisan, self.artisan_token = make_user('artisan1', 'Artisan')
        self.prop = make_property(self.landlord)
        self.unit = make_unit(self.prop, self.landlord)

    def auth(self, token):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

    def test_tenant_with_lease_can_submit_request(self):
        make_lease(self.unit, self.tenant)
        self.auth(self.tenant_token)
        data = {
            'property': self.prop.id, 'unit': self.unit.id,
            'title': 'Broken tap', 'description': 'Dripping.', 'category': 'plumbing', 'priority': 'low',
        }
        response = self.client.post(reverse('maintenance-request-list'), data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['submitted_by'], self.tenant.id)

    def test_tenant_without_lease_cannot_submit_request(self):
        self.auth(self.tenant_token)
        data = {
            'property': self.prop.id, 'unit': self.unit.id,
            'title': 'Broken tap', 'description': 'Dripping.', 'category': 'plumbing', 'priority': 'low',
        }
        response = self.client.post(reverse('maintenance-request-list'), data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_tenant_with_lease_can_submit_common_area_request(self):
        make_lease(self.unit, self.tenant)
        self.auth(self.tenant_token)
        data = {
            'property': self.prop.id,
            'title': 'Broken gate', 'description': 'Main gate.', 'category': 'electrical', 'priority': 'high',
        }
        response = self.client.post(reverse('maintenance-request-list'), data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_tenant_without_lease_cannot_submit_common_area_request(self):
        self.auth(self.tenant_token)
        data = {
            'property': self.prop.id,
            'title': 'Broken gate', 'description': 'Main gate.', 'category': 'electrical', 'priority': 'high',
        }
        response = self.client.post(reverse('maintenance-request-list'), data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_tenant_cannot_submit_for_unrelated_property(self):
        other_landlord, _ = make_user('landlord2', 'Landlord')
        other_prop = make_property(other_landlord)
        other_unit = make_unit(other_prop, other_landlord)
        make_lease(self.unit, self.tenant)  # lease on original property only
        self.auth(self.tenant_token)
        data = {
            'property': other_prop.id, 'unit': other_unit.id,
            'title': 'X', 'description': 'X', 'category': 'other', 'priority': 'low',
        }
        response = self.client.post(reverse('maintenance-request-list'), data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unit_from_different_property_is_rejected(self):
        other_landlord, _ = make_user('landlord2', 'Landlord')
        other_prop = make_property(other_landlord)
        other_unit = make_unit(other_prop, other_landlord)
        make_lease(self.unit, self.tenant)
        self.auth(self.tenant_token)
        data = {
            'property': self.prop.id, 'unit': other_unit.id,
            'title': 'X', 'description': 'X', 'category': 'other', 'priority': 'low',
        }
        response = self.client.post(reverse('maintenance-request-list'), data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_landlord_can_submit_for_own_property(self):
        self.auth(self.landlord_token)
        data = {
            'property': self.prop.id,
            'title': 'Gate broken', 'description': 'Main gate.', 'category': 'electrical', 'priority': 'high',
        }
        response = self.client.post(reverse('maintenance-request-list'), data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_landlord_cannot_submit_for_other_landlords_property(self):
        other_landlord, other_token = make_user('landlord2', 'Landlord')
        other_prop = make_property(other_landlord)
        self.auth(self.landlord_token)
        data = {
            'property': other_prop.id,
            'title': 'X', 'description': 'X', 'category': 'other', 'priority': 'low',
        }
        response = self.client.post(reverse('maintenance-request-list'), data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_agent_cannot_submit_request(self):
        self.auth(self.agent_token)
        data = {'property': self.prop.id, 'title': 'X', 'description': 'X', 'category': 'other', 'priority': 'low'}
        response = self.client.post(reverse('maintenance-request-list'), data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_artisan_cannot_submit_request(self):
        self.auth(self.artisan_token)
        data = {'property': self.prop.id, 'title': 'X', 'description': 'X', 'category': 'other', 'priority': 'low'}
        response = self.client.post(reverse('maintenance-request-list'), data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class RequestVisibilityTests(APITestCase):
    def setUp(self):
        self.landlord, self.landlord_token = make_user('landlord1', 'Landlord')
        self.tenant, self.tenant_token = make_user('tenant1', 'Tenant')
        self.other_tenant, self.other_token = make_user('tenant2', 'Tenant')
        self.agent, self.agent_token = make_user('agent1', 'Agent')
        self.artisan, self.artisan_token = make_user('artisan1', 'Artisan')
        ArtisanProfile.objects.create(user=self.artisan, trade='plumbing')

        self.prop = make_property(self.landlord)
        self.unit = make_unit(self.prop, self.landlord)
        self.req = make_request(self.prop, self.tenant, self.unit, req_status='open')

    def auth(self, token):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

    def test_tenant_sees_own_requests(self):
        self.auth(self.tenant_token)
        response = self.client.get(reverse('maintenance-request-list'))
        self.assertEqual(len(response.data), 1)

    def test_other_tenant_sees_no_requests(self):
        self.auth(self.other_token)
        response = self.client.get(reverse('maintenance-request-list'))
        self.assertEqual(len(response.data), 0)

    def test_landlord_sees_property_requests(self):
        self.auth(self.landlord_token)
        response = self.client.get(reverse('maintenance-request-list'))
        self.assertEqual(len(response.data), 1)

    def test_artisan_sees_open_requests_matching_trade(self):
        self.auth(self.artisan_token)
        response = self.client.get(reverse('maintenance-request-list'))
        self.assertEqual(len(response.data), 1)

    def test_artisan_does_not_see_different_trade_requests(self):
        self.artisan.artisan_profile.trade = 'electrical'
        self.artisan.artisan_profile.save()
        self.auth(self.artisan_token)
        response = self.client.get(reverse('maintenance-request-list'))
        self.assertEqual(len(response.data), 0)

    def test_assigned_agent_sees_requests(self):
        PropertyAgent.objects.create(property=self.prop, agent=self.agent, appointed_by=self.landlord)
        self.auth(self.agent_token)
        response = self.client.get(reverse('maintenance-request-list'))
        self.assertEqual(len(response.data), 1)


class StatusTransitionTests(APITestCase):
    def setUp(self):
        self.landlord, self.landlord_token = make_user('landlord1', 'Landlord')
        self.tenant, self.tenant_token = make_user('tenant1', 'Tenant')
        self.artisan, self.artisan_token = make_user('artisan1', 'Artisan')
        ArtisanProfile.objects.create(user=self.artisan, trade='plumbing')

        self.prop = make_property(self.landlord)
        self.unit = make_unit(self.prop, self.landlord)
        self.req = make_request(self.prop, self.tenant, self.unit)

    def auth(self, token):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

    def test_landlord_opens_request_for_bidding(self):
        self.auth(self.landlord_token)
        response = self.client.put(reverse('maintenance-request-detail', args=[self.req.id]), {'status': 'open'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'open')

    def test_tenant_cannot_open_request(self):
        self.auth(self.tenant_token)
        response = self.client.put(reverse('maintenance-request-detail', args=[self.req.id]), {'status': 'open'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_tenant_can_cancel_submitted_request(self):
        self.auth(self.tenant_token)
        response = self.client.put(reverse('maintenance-request-detail', args=[self.req.id]), {'status': 'cancelled'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_tenant_cannot_cancel_assigned_request(self):
        self.req.status = 'assigned'
        self.req.assigned_to = self.artisan
        self.req.save()
        self.auth(self.tenant_token)
        response = self.client.put(reverse('maintenance-request-detail', args=[self.req.id]), {'status': 'cancelled'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_artisan_marks_in_progress(self):
        self.req.status = 'assigned'
        self.req.assigned_to = self.artisan
        self.req.save()
        self.auth(self.artisan_token)
        response = self.client.put(reverse('maintenance-request-detail', args=[self.req.id]), {'status': 'in_progress'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_unassigned_artisan_cannot_mark_in_progress(self):
        other_artisan, other_token = make_user('artisan2', 'Artisan')
        self.req.status = 'assigned'
        self.req.assigned_to = self.artisan
        self.req.save()
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {other_token.key}')
        response = self.client.put(reverse('maintenance-request-detail', args=[self.req.id]), {'status': 'in_progress'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_tenant_marks_completed(self):
        self.req.status = 'in_progress'
        self.req.assigned_to = self.artisan
        self.req.save()
        self.auth(self.tenant_token)
        response = self.client.put(reverse('maintenance-request-detail', args=[self.req.id]), {'status': 'completed'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNotNone(response.data['resolved_at'])


class BiddingTests(APITestCase):
    def setUp(self):
        self.landlord, self.landlord_token = make_user('landlord1', 'Landlord')
        self.tenant, self.tenant_token = make_user('tenant1', 'Tenant')
        self.artisan, self.artisan_token = make_user('artisan1', 'Artisan')
        self.artisan2, self.artisan2_token = make_user('artisan2', 'Artisan')
        ArtisanProfile.objects.create(user=self.artisan, trade='plumbing')
        ArtisanProfile.objects.create(user=self.artisan2, trade='plumbing')

        self.prop = make_property(self.landlord)
        self.unit = make_unit(self.prop, self.landlord)
        self.req = make_request(self.prop, self.tenant, self.unit, req_status='open')

    def auth(self, token):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

    def test_artisan_can_bid(self):
        self.auth(self.artisan_token)
        data = {'proposed_price': '8500.00', 'message': 'Can fix in 2 days.'}
        response = self.client.post(reverse('maintenance-bid-list', args=[self.req.id]), data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_artisan_cannot_bid_twice(self):
        MaintenanceBid.objects.create(request=self.req, artisan=self.artisan, proposed_price='8500')
        self.auth(self.artisan_token)
        data = {'proposed_price': '7000.00'}
        response = self.client.post(reverse('maintenance-bid-list', args=[self.req.id]), data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_non_artisan_cannot_bid(self):
        self.auth(self.tenant_token)
        data = {'proposed_price': '8500.00'}
        response = self.client.post(reverse('maintenance-bid-list', args=[self.req.id]), data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_cannot_bid_on_non_open_request(self):
        self.req.status = 'submitted'
        self.req.save()
        self.auth(self.artisan_token)
        data = {'proposed_price': '8500.00'}
        response = self.client.post(reverse('maintenance-bid-list', args=[self.req.id]), data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_tenant_can_accept_bid(self):
        bid = MaintenanceBid.objects.create(request=self.req, artisan=self.artisan, proposed_price='8500')
        self.auth(self.tenant_token)
        response = self.client.put(
            reverse('maintenance-bid-detail', args=[self.req.id, bid.id]),
            {'status': 'accepted'}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.req.refresh_from_db()
        self.assertEqual(self.req.status, 'assigned')
        self.assertEqual(self.req.assigned_to, self.artisan)

    def test_accepting_bid_rejects_others(self):
        bid1 = MaintenanceBid.objects.create(request=self.req, artisan=self.artisan, proposed_price='8500')
        bid2 = MaintenanceBid.objects.create(request=self.req, artisan=self.artisan2, proposed_price='9000')
        self.auth(self.tenant_token)
        self.client.put(reverse('maintenance-bid-detail', args=[self.req.id, bid1.id]), {'status': 'accepted'})
        bid2.refresh_from_db()
        self.assertEqual(bid2.status, 'rejected')

    def test_landlord_can_accept_bid_on_their_request(self):
        landlord_req = make_request(self.prop, self.landlord, req_status='open')
        bid = MaintenanceBid.objects.create(request=landlord_req, artisan=self.artisan, proposed_price='8500')
        self.auth(self.landlord_token)
        response = self.client.put(
            reverse('maintenance-bid-detail', args=[landlord_req.id, bid.id]),
            {'status': 'accepted'}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_tenant_cannot_accept_bid_on_landlord_request(self):
        landlord_req = make_request(self.prop, self.landlord, req_status='open')
        bid = MaintenanceBid.objects.create(request=landlord_req, artisan=self.artisan, proposed_price='8500')
        self.auth(self.tenant_token)
        response = self.client.put(
            reverse('maintenance-bid-detail', args=[landlord_req.id, bid.id]),
            {'status': 'accepted'}
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_artisan_only_sees_own_bid(self):
        MaintenanceBid.objects.create(request=self.req, artisan=self.artisan, proposed_price='8500')
        MaintenanceBid.objects.create(request=self.req, artisan=self.artisan2, proposed_price='9000')
        self.auth(self.artisan_token)
        response = self.client.get(reverse('maintenance-bid-list', args=[self.req.id]))
        self.assertEqual(len(response.data), 1)

    def test_landlord_sees_all_bids(self):
        MaintenanceBid.objects.create(request=self.req, artisan=self.artisan, proposed_price='8500')
        MaintenanceBid.objects.create(request=self.req, artisan=self.artisan2, proposed_price='9000')
        self.auth(self.landlord_token)
        response = self.client.get(reverse('maintenance-bid-list', args=[self.req.id]))
        self.assertEqual(len(response.data), 2)


class NoteTests(APITestCase):
    def setUp(self):
        self.landlord, self.landlord_token = make_user('landlord1', 'Landlord')
        self.tenant, self.tenant_token = make_user('tenant1', 'Tenant')
        self.other_tenant, self.other_token = make_user('tenant2', 'Tenant')
        self.prop = make_property(self.landlord)
        self.unit = make_unit(self.prop, self.landlord)
        self.req = make_request(self.prop, self.tenant, self.unit)

    def auth(self, token):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

    def test_submitter_can_add_note(self):
        self.auth(self.tenant_token)
        response = self.client.post(
            reverse('maintenance-note-list', args=[self.req.id]),
            {'note': 'Please come before 5pm.'}
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['author'], self.tenant.id)

    def test_landlord_can_add_note(self):
        self.auth(self.landlord_token)
        response = self.client.post(
            reverse('maintenance-note-list', args=[self.req.id]),
            {'note': 'Scheduled for Friday.'}
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_unrelated_tenant_cannot_add_note(self):
        self.auth(self.other_token)
        response = self.client.post(
            reverse('maintenance-note-list', args=[self.req.id]),
            {'note': 'Uninvited.'}
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
