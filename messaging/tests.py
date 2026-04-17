from datetime import date

from django.urls import reverse
from django.test.utils import override_settings
from rest_framework.test import APITestCase
from rest_framework.authtoken.models import Token

from authentication.models import CustomUser, MovingCompanyProfile, Role
from maintenance.models import MaintenanceBid, MaintenanceRequest
from moving.models import MovingBooking
from property.models import Lease, Property, PropertyAgent, Unit
from .models import Conversation, ConversationParticipant, Message


def make_user(username, role_name):
    role, _ = Role.objects.get_or_create(name=role_name)
    user = CustomUser.objects.create_user(username=username, password='testpass', role=role)
    token = Token.objects.create(user=user)
    return user, token


class ConversationListCreateTests(APITestCase):

    def setUp(self):
        self.landlord, self.landlord_token = make_user('landlord1', Role.LANDLORD)
        self.tenant, self.tenant_token = make_user('tenant1', Role.TENANT)
        self.tenant2, self.tenant2_token = make_user('tenant2', Role.TENANT)

        # Create a conversation between landlord and tenant
        self.conversation = Conversation.objects.create(
            subject='Test conversation',
            created_by=self.landlord,
        )
        ConversationParticipant.objects.create(conversation=self.conversation, user=self.landlord)
        ConversationParticipant.objects.create(conversation=self.conversation, user=self.tenant)

        self.list_url = reverse('conversation-list-create')

    def test_list_own_conversations(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.landlord_token.key}')
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, 200)
        ids = [c['id'] for c in response.data]
        self.assertIn(self.conversation.id, ids)

    def test_non_participant_cannot_see_conversation(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.tenant2_token.key}')
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, 200)
        ids = [c['id'] for c in response.data]
        self.assertNotIn(self.conversation.id, ids)

    def test_create_conversation(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.landlord_token.key}')
        data = {
            'subject': 'New conversation',
            'participant_ids': [self.tenant.id],
        }
        response = self.client.post(self.list_url, data, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['subject'], 'New conversation')
        participant_user_ids = [p['user_id'] for p in response.data['participants']]
        self.assertIn(self.landlord.id, participant_user_ids)
        self.assertIn(self.tenant.id, participant_user_ids)

    def test_create_conversation_no_participants(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.landlord_token.key}')
        data = {'subject': 'Empty conversation', 'participant_ids': []}
        response = self.client.post(self.list_url, data, format='json')
        self.assertEqual(response.status_code, 400)

    def test_unauthenticated(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, 401)


class ConversationDetailTests(APITestCase):

    def setUp(self):
        self.landlord, self.landlord_token = make_user('landlord2', Role.LANDLORD)
        self.tenant, self.tenant_token = make_user('tenant3', Role.TENANT)
        self.outsider, self.outsider_token = make_user('outsider', Role.TENANT)

        self.conversation = Conversation.objects.create(
            subject='Detail test',
            created_by=self.landlord,
        )
        ConversationParticipant.objects.create(conversation=self.conversation, user=self.landlord)
        ConversationParticipant.objects.create(conversation=self.conversation, user=self.tenant)

    def _detail_url(self, pk):
        return reverse('conversation-detail', args=[pk])

    def test_participant_can_retrieve(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.landlord_token.key}')
        response = self.client.get(self._detail_url(self.conversation.pk))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['id'], self.conversation.id)

    def test_non_participant_gets_403(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.outsider_token.key}')
        response = self.client.get(self._detail_url(self.conversation.pk))
        self.assertEqual(response.status_code, 403)

    def test_nonexistent_gets_404(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.landlord_token.key}')
        response = self.client.get(self._detail_url(99999))
        self.assertEqual(response.status_code, 404)


class MessageTests(APITestCase):

    def setUp(self):
        self.landlord, self.landlord_token = make_user('landlord3', Role.LANDLORD)
        self.tenant, self.tenant_token = make_user('tenant4', Role.TENANT)
        self.outsider, self.outsider_token = make_user('outsider2', Role.TENANT)

        self.conversation = Conversation.objects.create(
            subject='Message test',
            created_by=self.landlord,
        )
        ConversationParticipant.objects.create(conversation=self.conversation, user=self.landlord)
        ConversationParticipant.objects.create(conversation=self.conversation, user=self.tenant)

        Message.objects.create(
            conversation=self.conversation,
            sender=self.landlord,
            body='Hello tenant!',
        )

    def _messages_url(self, pk):
        return reverse('message-list-create', args=[pk])

    def test_participant_can_list_messages(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.landlord_token.key}')
        response = self.client.get(self._messages_url(self.conversation.pk))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['body'], 'Hello tenant!')

    def test_participant_can_send_message(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.tenant_token.key}')
        response = self.client.post(
            self._messages_url(self.conversation.pk),
            {'body': 'Hi landlord!'},
            format='json',
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['body'], 'Hi landlord!')
        self.assertEqual(response.data['sender'], self.tenant.id)

    def test_non_participant_cannot_send(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.outsider_token.key}')
        response = self.client.post(
            self._messages_url(self.conversation.pk),
            {'body': 'Intruder message'},
            format='json',
        )
        self.assertEqual(response.status_code, 403)

    def test_empty_body_is_rejected(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.landlord_token.key}')
        response = self.client.post(
            self._messages_url(self.conversation.pk),
            {'body': ''},
            format='json',
        )
        self.assertEqual(response.status_code, 400)

    def test_nonexistent_conversation_get_messages_returns_404(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.landlord_token.key}')
        response = self.client.get(self._messages_url(99999))
        self.assertEqual(response.status_code, 404)

    def test_nonexistent_conversation_post_message_returns_404(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.landlord_token.key}')
        response = self.client.post(self._messages_url(99999), {'body': 'hello'}, format='json')
        self.assertEqual(response.status_code, 404)


class ConversationMarkReadTests(APITestCase):

    def setUp(self):
        self.landlord, self.landlord_token = make_user('landlord4', Role.LANDLORD)
        self.tenant, self.tenant_token = make_user('tenant5', Role.TENANT)
        self.outsider, self.outsider_token = make_user('outsider3', Role.TENANT)

        self.conversation = Conversation.objects.create(
            subject='Mark read test',
            created_by=self.landlord,
        )
        ConversationParticipant.objects.create(
            conversation=self.conversation,
            user=self.landlord,
            last_read_at=None,
        )
        ConversationParticipant.objects.create(
            conversation=self.conversation,
            user=self.tenant,
            last_read_at=None,
        )

        Message.objects.create(
            conversation=self.conversation,
            sender=self.landlord,
            body='Unread message',
        )

    def _read_url(self, pk):
        return reverse('conversation-mark-read', args=[pk])

    def test_mark_read_updates_last_read_at(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.tenant_token.key}')
        response = self.client.post(self._read_url(self.conversation.pk))
        self.assertEqual(response.status_code, 200)
        participant = ConversationParticipant.objects.get(
            conversation=self.conversation,
            user=self.tenant,
        )
        self.assertIsNotNone(participant.last_read_at)

    def test_mark_read_returns_unread_count_zero(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.tenant_token.key}')
        response = self.client.post(self._read_url(self.conversation.pk))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['unread_count'], 0)

    def test_non_participant_cannot_mark_read(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.outsider_token.key}')
        response = self.client.post(self._read_url(self.conversation.pk))
        self.assertEqual(response.status_code, 403)


class ConversationParticipantPayloadTests(APITestCase):
    """Schema + primary_recipient + last_message shape; backward-compatible keys."""

    def setUp(self):
        self.landlord, self.landlord_token = make_user('schema_landlord', Role.LANDLORD)
        self.tenant_a, self.tenant_a_token = make_user('schema_tenant_a', Role.TENANT)
        self.tenant_b, self.tenant_b_token = make_user('schema_tenant_b', Role.TENANT)

        self.landlord.email = 'landlord@example.com'
        self.landlord.phone = '+10001'
        self.landlord.first_name = 'Lou'
        self.landlord.last_name = 'Owner'
        self.landlord.save()

        self.tenant_a.email = 'a@example.com'
        self.tenant_a.phone = '+10002'
        self.tenant_a.first_name = 'Ann'
        self.tenant_a.last_name = 'Tenant'
        self.tenant_a.save()

        self.tenant_b.first_name = 'Bob'
        self.tenant_b.last_name = 'Other'
        self.tenant_b.save()

        self.group_conv = Conversation.objects.create(
            subject='Group chat',
            created_by=self.landlord,
        )
        ConversationParticipant.objects.create(conversation=self.group_conv, user=self.landlord)
        ConversationParticipant.objects.create(conversation=self.group_conv, user=self.tenant_a)
        ConversationParticipant.objects.create(conversation=self.group_conv, user=self.tenant_b)

        Message.objects.create(
            conversation=self.group_conv,
            sender=self.tenant_b,
            body='Hello group',
        )

    def _assert_participant_shape(self, p, viewer: CustomUser):
        self.assertIn('id', p)
        self.assertIn('user_id', p)
        self.assertIn('user', p)
        self.assertEqual(p['user_id'], p['user'])
        self.assertIn('full_name', p)
        self.assertIn('email', p)
        self.assertIn('phone', p)
        self.assertIn('role', p)
        self.assertIn('avatar_url', p)
        self.assertIsNone(p['avatar_url'])
        self.assertIn('is_self', p)
        self.assertEqual(p['is_self'], p['user_id'] == viewer.id)
        self.assertIn('last_read_at', p)
        self.assertIn('joined_at', p)
        self.assertIn('username', p)
        self.assertIn('first_name', p)
        self.assertIn('last_name', p)

    def _assert_last_message_shape(self, lm, expected_sender_id):
        self.assertIsNotNone(lm)
        for key in ('id', 'sender', 'sender_name', 'body', 'created_at'):
            self.assertIn(key, lm)
        self.assertEqual(lm['sender'], expected_sender_id)
        self.assertEqual(lm['sender_id'], expected_sender_id)
        self.assertIn('sender_username', lm)

    def test_list_participants_primary_recipient_and_last_message(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.landlord_token.key}')
        response = self.client.get(reverse('conversation-list-create'))
        self.assertEqual(response.status_code, 200)
        row = next(c for c in response.data if c['id'] == self.group_conv.id)

        self.assertIn('primary_recipient', row)
        pr = row['primary_recipient']
        self.assertIsNotNone(pr)
        self.assertEqual(pr['user_id'], self.tenant_a.id)
        self.assertEqual(pr['full_name'], 'Ann Tenant')
        self.assertEqual(pr['email'], 'a@example.com')
        self.assertEqual(pr['phone'], '+10002')
        self.assertEqual(pr['role'], Role.TENANT)
        self.assertIsNone(pr['avatar_url'])

        for p in row['participants']:
            self._assert_participant_shape(p, self.landlord)

        self._assert_last_message_shape(row['last_message'], self.tenant_b.id)
        self.assertEqual(row['last_message']['sender_username'], self.tenant_b.username)

    def test_detail_tenant_primary_recipient_is_landlord(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.tenant_a_token.key}')
        response = self.client.get(reverse('conversation-detail', args=[self.group_conv.pk]))
        self.assertEqual(response.status_code, 200)
        pr = response.data['primary_recipient']
        self.assertIsNotNone(pr)
        self.assertEqual(pr['user_id'], self.landlord.id)
        self.assertEqual(pr['full_name'], 'Lou Owner')

    def test_group_chat_primary_recipient_first_non_self_by_participant_id_order(self):
        """Non-landlord participant: first other by participant pk order is landlord."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.tenant_b_token.key}')
        response = self.client.get(reverse('conversation-detail', args=[self.group_conv.pk]))
        self.assertEqual(response.status_code, 200)
        pr = response.data['primary_recipient']
        self.assertIsNotNone(pr)
        self.assertEqual(pr['user_id'], self.landlord.id)

    @override_settings(DEBUG=True)
    def test_list_and_detail_query_count_stays_bounded(self):
        """List/detail use one annotated conversation query + prefetch; no N+1 on participants."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.landlord_token.key}')
        with self.assertNumQueries(3, using='default'):
            response = self.client.get(reverse('conversation-list-create'))
        self.assertEqual(response.status_code, 200)
        with self.assertNumQueries(3, using='default'):
            response = self.client.get(reverse('conversation-detail', args=[self.group_conv.pk]))
        self.assertEqual(response.status_code, 200)


class MessagingParticipantsLookupTests(APITestCase):
    """GET /api/messaging/participants/ — role-scoped compose directory."""

    def setUp(self):
        self.landlord, self.landlord_token = make_user('mplandlord', Role.LANDLORD)
        self.agent, self.agent_token = make_user('mpagent', Role.AGENT)
        self.tenant, self.tenant_token = make_user('mptenant', Role.TENANT)
        self.stranger, self.stranger_token = make_user('mpstranger', Role.TENANT)
        self.admin, self.admin_token = make_user('mpadmin', Role.ADMIN)
        self.admin.is_staff = True
        self.admin.save()

        self.tenant.email = 'tenant.mail@example.com'
        self.tenant.phone = '+15550001111'
        self.tenant.first_name = 'Pat'
        self.tenant.last_name = 'Leaseholder'
        self.tenant.save()

        self.prop_a = Property.objects.create(
            name='Prop A',
            property_type='apartment',
            owner=self.landlord,
            created_by=self.landlord,
        )
        self.prop_b = Property.objects.create(
            name='Prop B',
            property_type='house',
            owner=self.landlord,
            created_by=self.landlord,
        )
        self.unit_a = Unit.objects.create(
            property=self.prop_a,
            name='A1',
            created_by=self.landlord,
            is_occupied=True,
        )
        self.unit_b = Unit.objects.create(
            property=self.prop_b,
            name='B1',
            created_by=self.landlord,
            is_occupied=True,
        )
        Lease.objects.create(
            unit=self.unit_a,
            tenant=self.tenant,
            start_date=date.today(),
            rent_amount=100,
            is_active=True,
        )
        PropertyAgent.objects.create(
            property=self.prop_a,
            agent=self.agent,
            appointed_by=self.landlord,
        )

        self.artisan, self.artisan_token = make_user('mpartisan', Role.ARTISAN)
        self.mreq = MaintenanceRequest.objects.create(
            property=self.prop_a,
            unit=self.unit_a,
            submitted_by=self.tenant,
            title='Tap',
            description='Drip',
            category='plumbing',
        )
        MaintenanceBid.objects.create(
            request=self.mreq,
            artisan=self.artisan,
            proposed_price=50,
        )

        self.mover, self.mover_token = make_user('mpmover', Role.MOVING_COMPANY)
        self.mover_profile = MovingCompanyProfile.objects.create(
            user=self.mover,
            company_name='Movers Inc',
        )
        MovingBooking.objects.create(
            company=self.mover_profile,
            customer=self.tenant,
            moving_date=date.today(),
            moving_time='10:00:00',
            pickup_address='A',
            delivery_address='B',
        )

        self.url = reverse('messaging-participants-lookup')

    def _ids(self, response):
        return {row['user_id'] for row in response.data['results']}

    def test_landlord_sees_tenant_and_agent_not_stranger(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.landlord_token.key}')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        ids = self._ids(response)
        self.assertIn(self.tenant.id, ids)
        self.assertIn(self.agent.id, ids)
        self.assertNotIn(self.stranger.id, ids)
        self.assertNotIn(self.landlord.id, ids)

    def test_tenant_sees_landlord_agent_and_moving_company(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.tenant_token.key}')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        ids = self._ids(response)
        self.assertIn(self.landlord.id, ids)
        self.assertIn(self.agent.id, ids)
        self.assertIn(self.mover.id, ids)
        self.assertNotIn(self.stranger.id, ids)

    def test_agent_sees_landlord_and_tenant(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.agent_token.key}')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        ids = self._ids(response)
        self.assertIn(self.landlord.id, ids)
        self.assertIn(self.tenant.id, ids)

    def test_admin_includes_unrelated_user(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.admin_token.key}')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        ids = self._ids(response)
        self.assertIn(self.stranger.id, ids)

    def test_artisan_sees_submitter_and_owner(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.artisan_token.key}')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        ids = self._ids(response)
        self.assertIn(self.tenant.id, ids)
        self.assertIn(self.landlord.id, ids)

    def test_moving_company_sees_counterparty(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.mover_token.key}')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        ids = self._ids(response)
        self.assertIn(self.tenant.id, ids)

    def test_search_email_phone_and_full_name(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.landlord_token.key}')
        r1 = self.client.get(self.url, {'search': 'tenant.mail@example.com'})
        self.assertEqual(r1.status_code, 200)
        self.assertEqual(self._ids(r1), {self.tenant.id})

        r2 = self.client.get(self.url, {'search': '+15550001111'})
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(self._ids(r2), {self.tenant.id})

        r3 = self.client.get(self.url, {'search': 'Pat Leaseholder'})
        self.assertEqual(r3.status_code, 200)
        self.assertEqual(self._ids(r3), {self.tenant.id})

    def test_property_filter_narrows_to_that_property(self):
        other_tenant, _ = make_user('mpother_t', Role.TENANT)
        Lease.objects.create(
            unit=self.unit_b,
            tenant=other_tenant,
            start_date=date.today(),
            rent_amount=200,
            is_active=True,
        )
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.landlord_token.key}')
        response = self.client.get(self.url, {'property': self.prop_a.id})
        self.assertEqual(response.status_code, 200)
        ids = self._ids(response)
        self.assertIn(self.tenant.id, ids)
        self.assertIn(self.agent.id, ids)
        self.assertNotIn(other_tenant.id, ids)

    def test_property_filter_forbidden_for_unrelated_tenant(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.stranger_token.key}')
        response = self.client.get(self.url, {'property': self.prop_a.id})
        self.assertEqual(response.status_code, 403)

    def test_moving_company_property_filter_bad_request(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.mover_token.key}')
        response = self.client.get(self.url, {'property': self.prop_a.id})
        self.assertEqual(response.status_code, 400)

    def test_invalid_limit_returns_400(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.landlord_token.key}')
        response = self.client.get(self.url, {'limit': 'x'})
        self.assertEqual(response.status_code, 400)

    def test_unauthenticated_401(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 401)

    def test_result_row_shape(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.landlord_token.key}')
        response = self.client.get(self.url, {'search': self.tenant.username})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 1)
        row = response.data['results'][0]
        for key in (
            'user_id',
            'full_name',
            'email',
            'phone',
            'role',
            'avatar_url',
            'is_active',
        ):
            self.assertIn(key, row)
        self.assertEqual(row['user_id'], self.tenant.id)
        self.assertIsNone(row['avatar_url'])
        self.assertEqual(row['role'], Role.TENANT)

    @override_settings(DEBUG=True)
    def test_lookup_query_count_bounded(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.landlord_token.key}')
        # Token auth + occasional role fetch + one eligible-users SELECT (select_related role).
        with self.assertNumQueries(3, using='default'):
            response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
