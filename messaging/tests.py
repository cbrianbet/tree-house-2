from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework.authtoken.models import Token

from authentication.models import CustomUser, Role
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
