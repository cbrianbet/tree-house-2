from datetime import date, timedelta

from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework.authtoken.models import Token
from rest_framework import status
from django.contrib.auth import get_user_model
from authentication.models import Role
from .models import Property, Unit, PropertyAgent, Lease, TenantApplication, LeaseDocument, PropertyReview, TenantReview

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


def make_property(owner):
    return Property.objects.create(name='Test Property', property_type='apartment', owner=owner, created_by=owner)


def make_unit(prop, owner, is_public=True):
    return Unit.objects.create(property=prop, name='Unit 1', price='45000', created_by=owner, is_public=is_public)


def make_lease(unit, tenant, end_date=None):
    return Lease.objects.create(
        unit=unit, tenant=tenant,
        start_date=date.today(),
        end_date=end_date,
        rent_amount='45000',
        is_active=True,
    )


class TenantApplicationTests(APITestCase):
    def setUp(self):
        self.landlord, self.landlord_token = make_user('landlord1', 'Landlord')
        self.tenant, self.tenant_token = make_user('tenant1', 'Tenant')
        self.tenant2, self.tenant2_token = make_user('tenant2', 'Tenant')
        self.agent, self.agent_token = make_user('agent1', 'Agent')
        self.prop = make_property(self.landlord)
        self.unit = make_unit(self.prop, self.landlord)

    def auth(self, token):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

    def test_tenant_can_submit_application(self):
        self.auth(self.tenant_token)
        response = self.client.post(reverse('application-list'), {
            'unit': self.unit.id, 'message': 'I am interested.',
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['applicant'], self.tenant.id)
        self.assertEqual(response.data['status'], 'pending')

    def test_non_tenant_cannot_apply(self):
        self.auth(self.agent_token)
        response = self.client.post(reverse('application-list'), {'unit': self.unit.id})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_cannot_apply_to_occupied_unit(self):
        self.unit.is_occupied = True
        self.unit.save()
        self.auth(self.tenant_token)
        response = self.client.post(reverse('application-list'), {'unit': self.unit.id})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_duplicate_application_rejected(self):
        TenantApplication.objects.create(unit=self.unit, applicant=self.tenant)
        self.auth(self.tenant_token)
        response = self.client.post(reverse('application-list'), {'unit': self.unit.id})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_landlord_sees_own_applications(self):
        TenantApplication.objects.create(unit=self.unit, applicant=self.tenant)
        self.auth(self.landlord_token)
        response = self.client.get(reverse('application-list'))
        self.assertEqual(len(response.data), 1)

    def test_tenant_sees_own_applications_only(self):
        TenantApplication.objects.create(unit=self.unit, applicant=self.tenant)
        TenantApplication.objects.create(unit=self.unit, applicant=self.tenant2)
        self.auth(self.tenant_token)
        response = self.client.get(reverse('application-list'))
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['applicant'], self.tenant.id)

    def test_landlord_can_approve_application(self):
        app = TenantApplication.objects.create(unit=self.unit, applicant=self.tenant)
        self.auth(self.landlord_token)
        response = self.client.put(reverse('application-detail', args=[app.id]), {
            'status': 'approved',
            'start_date': str(date.today()),
            'end_date': str(date.today() + timedelta(days=365)),
            'rent_amount': '45000.00',
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'approved')
        # Lease created
        self.unit.refresh_from_db()
        self.assertTrue(self.unit.is_occupied)
        self.assertTrue(Lease.objects.filter(unit=self.unit, tenant=self.tenant).exists())

    def test_approval_rejects_competing_applications(self):
        app1 = TenantApplication.objects.create(unit=self.unit, applicant=self.tenant)
        app2 = TenantApplication.objects.create(unit=self.unit, applicant=self.tenant2)
        self.auth(self.landlord_token)
        self.client.put(reverse('application-detail', args=[app1.id]), {
            'status': 'approved',
            'start_date': str(date.today()),
            'rent_amount': '45000.00',
        })
        app2.refresh_from_db()
        self.assertEqual(app2.status, 'rejected')

    def test_approval_requires_start_date_and_rent(self):
        app = TenantApplication.objects.create(unit=self.unit, applicant=self.tenant)
        self.auth(self.landlord_token)
        response = self.client.put(reverse('application-detail', args=[app.id]), {'status': 'approved'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_landlord_can_reject_application(self):
        app = TenantApplication.objects.create(unit=self.unit, applicant=self.tenant)
        self.auth(self.landlord_token)
        response = self.client.put(reverse('application-detail', args=[app.id]), {'status': 'rejected'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'rejected')

    def test_tenant_can_withdraw_application(self):
        app = TenantApplication.objects.create(unit=self.unit, applicant=self.tenant)
        self.auth(self.tenant_token)
        response = self.client.put(reverse('application-detail', args=[app.id]), {'status': 'withdrawn'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'withdrawn')

    def test_tenant_cannot_approve(self):
        app = TenantApplication.objects.create(unit=self.unit, applicant=self.tenant)
        self.auth(self.tenant_token)
        response = self.client.put(reverse('application-detail', args=[app.id]), {
            'status': 'approved', 'start_date': str(date.today()), 'rent_amount': '45000.00',
        })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_other_landlord_cannot_access_application(self):
        other_landlord, other_token = make_user('landlord2', 'Landlord')
        app = TenantApplication.objects.create(unit=self.unit, applicant=self.tenant)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {other_token.key}')
        response = self.client.get(reverse('application-detail', args=[app.id]))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class LandlordDashboardTests(APITestCase):
    def setUp(self):
        self.landlord, self.landlord_token = make_user('landlord1', 'Landlord')
        self.tenant, self.tenant_token = make_user('tenant1', 'Tenant')
        self.prop = make_property(self.landlord)
        self.unit = make_unit(self.prop, self.landlord)

    def auth(self, token):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

    def test_landlord_can_access_dashboard(self):
        self.auth(self.landlord_token)
        response = self.client.get(reverse('landlord-dashboard'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('properties', response.data)
        self.assertIn('adverts', response.data)
        self.assertIn('applications', response.data)
        self.assertIn('leases_ending_soon', response.data)
        self.assertIn('billing', response.data)
        self.assertIn('maintenance', response.data)
        self.assertIn('performance', response.data)

    def test_tenant_cannot_access_dashboard(self):
        self.auth(self.tenant_token)
        response = self.client.get(reverse('landlord-dashboard'))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_vacant_unit_count(self):
        self.auth(self.landlord_token)
        response = self.client.get(reverse('landlord-dashboard'))
        self.assertEqual(response.data['properties']['vacant_units'], 1)
        self.assertEqual(response.data['properties']['occupied_units'], 0)

    def test_advert_appears_when_public_and_vacant(self):
        self.auth(self.landlord_token)
        response = self.client.get(reverse('landlord-dashboard'))
        self.assertEqual(response.data['adverts']['count'], 1)

    def test_advert_disappears_when_occupied(self):
        self.unit.is_occupied = True
        self.unit.save()
        self.auth(self.landlord_token)
        response = self.client.get(reverse('landlord-dashboard'))
        self.assertEqual(response.data['adverts']['count'], 0)

    def test_pending_application_counted(self):
        TenantApplication.objects.create(unit=self.unit, applicant=self.tenant)
        self.auth(self.landlord_token)
        response = self.client.get(reverse('landlord-dashboard'))
        self.assertEqual(response.data['applications']['pending'], 1)

    def test_lease_ending_within_60_days_shown(self):
        lease = make_lease(self.unit, self.tenant, end_date=date.today() + timedelta(days=30))
        self.unit.is_occupied = True
        self.unit.save()
        self.auth(self.landlord_token)
        response = self.client.get(reverse('landlord-dashboard'))
        self.assertEqual(len(response.data['leases_ending_soon']), 1)
        self.assertEqual(response.data['leases_ending_soon'][0]['days_remaining'], 30)

    def test_lease_ending_far_future_not_shown(self):
        make_lease(self.unit, self.tenant, end_date=date.today() + timedelta(days=120))
        self.unit.is_occupied = True
        self.unit.save()
        self.auth(self.landlord_token)
        response = self.client.get(reverse('landlord-dashboard'))
        self.assertEqual(len(response.data['leases_ending_soon']), 0)

    def test_performance_section_present(self):
        self.auth(self.landlord_token)
        response = self.client.get(reverse('landlord-dashboard'))
        perf = response.data['performance']
        self.assertIn('period', perf)
        self.assertIn('by_property', perf)
        self.assertEqual(len(perf['by_property']), 1)
        self.assertEqual(perf['by_property'][0]['name'], self.prop.name)


class LeaseDocumentTests(APITestCase):
    def setUp(self):
        self.landlord, self.landlord_token = make_user('landlord1', 'Landlord')
        self.tenant, self.tenant_token = make_user('tenant1', 'Tenant')
        self.agent, self.agent_token = make_user('agent1', 'Agent')
        self.other_user, self.other_token = make_user('other1', 'Tenant')

        self.prop = make_property(self.landlord)
        self.unit = make_unit(self.prop, self.landlord)
        self.lease = make_lease(self.unit, self.tenant)

        PropertyAgent.objects.create(property=self.prop, agent=self.agent, appointed_by=self.landlord)

    def auth(self, token):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

    def _doc_list_url(self):
        return reverse('lease-document-list-create', args=[self.lease.id])

    def _doc_sign_url(self, doc_id):
        return reverse('lease-document-sign', args=[self.lease.id, doc_id])

    def _make_doc(self):
        return LeaseDocument.objects.create(
            lease=self.lease,
            document_type='lease_agreement',
            title='Test Doc',
            file_url='https://example.com/doc.pdf',
            uploaded_by=self.landlord,
        )

    def test_landlord_can_upload_document(self):
        self.auth(self.landlord_token)
        response = self.client.post(self._doc_list_url(), {
            'document_type': 'lease_agreement',
            'title': 'Main Lease',
            'file_url': 'https://example.com/lease.pdf',
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['uploaded_by'], self.landlord.id)

    def test_tenant_can_list_documents(self):
        self._make_doc()
        self.auth(self.tenant_token)
        response = self.client.get(self._doc_list_url())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_agent_can_upload_document(self):
        self.auth(self.agent_token)
        response = self.client.post(self._doc_list_url(), {
            'document_type': 'notice',
            'title': 'Agent Notice',
            'file_url': 'https://example.com/notice.pdf',
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_unrelated_user_cannot_list(self):
        self.auth(self.other_token)
        response = self.client.get(self._doc_list_url())
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_tenant_can_sign_document(self):
        doc = self._make_doc()
        self.auth(self.tenant_token)
        response = self.client.post(self._doc_sign_url(doc.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['signed_by'], self.tenant.id)
        self.assertIsNotNone(response.data['signed_at'])

    def test_cannot_sign_twice(self):
        doc = self._make_doc()
        doc.signed_by = self.tenant
        from django.utils import timezone
        doc.signed_at = timezone.now()
        doc.save()
        self.auth(self.tenant_token)
        response = self.client.post(self._doc_sign_url(doc.id))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_only_tenant_can_sign(self):
        doc = self._make_doc()
        self.auth(self.landlord_token)
        response = self.client.post(self._doc_sign_url(doc.id))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class PropertyReviewTests(APITestCase):
    def setUp(self):
        self.landlord, self.landlord_token = make_user('landlord1', 'Landlord')
        self.tenant, self.tenant_token = make_user('tenant1', 'Tenant')
        self.tenant_no_lease, self.tenant_no_lease_token = make_user('tenant2', 'Tenant')

        self.prop = make_property(self.landlord)
        self.unit = make_unit(self.prop, self.landlord)
        self.lease = make_lease(self.unit, self.tenant)

    def auth(self, token):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

    def _list_url(self):
        return reverse('property-review-list-create', args=[self.prop.id])

    def _detail_url(self, review_id):
        return reverse('property-review-detail', args=[self.prop.id, review_id])

    def test_tenant_with_lease_can_review(self):
        self.auth(self.tenant_token)
        response = self.client.post(self._list_url(), {'rating': 4, 'comment': 'Good place.'})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['rating'], 4)

    def test_tenant_without_lease_cannot_review(self):
        self.auth(self.tenant_no_lease_token)
        response = self.client.post(self._list_url(), {'rating': 3, 'comment': 'Nice.'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_duplicate_review_rejected(self):
        PropertyReview.objects.create(reviewer=self.tenant, property=self.prop, rating=4)
        self.auth(self.tenant_token)
        response = self.client.post(self._list_url(), {'rating': 5, 'comment': 'Again.'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_landlord_cannot_review_property(self):
        self.auth(self.landlord_token)
        response = self.client.post(self._list_url(), {'rating': 5, 'comment': 'My own property.'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_reviewer_can_update_own_review(self):
        review = PropertyReview.objects.create(reviewer=self.tenant, property=self.prop, rating=3)
        self.auth(self.tenant_token)
        response = self.client.patch(self._detail_url(review.id), {'rating': 5, 'comment': 'Updated.'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['rating'], 5)

    def test_reviewer_can_delete_own_review(self):
        review = PropertyReview.objects.create(reviewer=self.tenant, property=self.prop, rating=3)
        self.auth(self.tenant_token)
        response = self.client.delete(self._detail_url(review.id))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(PropertyReview.objects.filter(pk=review.id).exists())

    def test_other_user_cannot_edit_review(self):
        review = PropertyReview.objects.create(reviewer=self.tenant, property=self.prop, rating=3)
        self.auth(self.tenant_no_lease_token)
        response = self.client.patch(self._detail_url(review.id), {'rating': 1})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class TenantReviewTests(APITestCase):
    def setUp(self):
        self.landlord, self.landlord_token = make_user('landlord1', 'Landlord')
        self.tenant, self.tenant_token = make_user('tenant1', 'Tenant')
        self.tenant2, self.tenant2_token = make_user('tenant2', 'Tenant')

        self.prop = make_property(self.landlord)
        self.unit = make_unit(self.prop, self.landlord)
        self.lease = make_lease(self.unit, self.tenant)

    def auth(self, token):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

    def _list_url(self):
        return reverse('tenant-review-list-create', args=[self.prop.id])

    def _detail_url(self, review_id):
        return reverse('tenant-review-detail', args=[self.prop.id, review_id])

    def test_landlord_can_review_tenant(self):
        self.auth(self.landlord_token)
        response = self.client.post(self._list_url(), {
            'tenant': self.tenant.id,
            'rating': 5,
            'comment': 'Great tenant.',
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['rating'], 5)

    def test_landlord_cannot_review_tenant_without_lease(self):
        self.auth(self.landlord_token)
        response = self.client.post(self._list_url(), {
            'tenant': self.tenant2.id,
            'rating': 4,
            'comment': 'No lease.',
        })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_tenant_cannot_review_another_tenant(self):
        self.auth(self.tenant_token)
        response = self.client.post(self._list_url(), {
            'tenant': self.tenant2.id,
            'rating': 3,
            'comment': 'Not allowed.',
        })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_public_view_shows_name_not_pii(self):
        TenantReview.objects.create(
            reviewer=self.landlord, tenant=self.tenant, property=self.prop, rating=4
        )
        self.auth(self.landlord_token)
        response = self.client.get(self._list_url())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        review_data = response.data[0]
        # name fields present
        self.assertIn('tenant_name', review_data)
        self.assertIn('reviewer_name', review_data)
        # PII fields must NOT be present
        self.assertNotIn('national_id', review_data)
        self.assertNotIn('emergency_contact_name', review_data)
        self.assertNotIn('emergency_contact_phone', review_data)

    def test_reviewer_can_update_own_review(self):
        review = TenantReview.objects.create(
            reviewer=self.landlord, tenant=self.tenant, property=self.prop, rating=3
        )
        self.auth(self.landlord_token)
        response = self.client.patch(self._detail_url(review.id), {'rating': 4, 'comment': 'Updated.'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['rating'], 4)

    def test_duplicate_review_rejected(self):
        TenantReview.objects.create(
            reviewer=self.landlord, tenant=self.tenant, property=self.prop, rating=5
        )
        self.auth(self.landlord_token)
        response = self.client.post(self._list_url(), {
            'tenant': self.tenant.id,
            'rating': 4,
            'comment': 'Duplicate.',
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
