"""
API contract tests: stable JSON shape for messaging list/detail and participant directory.

Sample list row (landlord viewing a 1:1 thread with a tenant who sent the last message):

{
  "id": 1,
  "property": null,
  "subject": "Contract conversation",
  "created_by": 10,
  "created_at": "2026-04-17T12:00:00Z",
  "participants": [
    {
      "id": 1,
      "user_id": 10,
      "user": 10,
      "username": "contract_ll",
      "first_name": "",
      "last_name": "",
      "full_name": "contract_ll",
      "email": "",
      "phone": "",
      "role": "Landlord",
      "avatar_url": null,
      "is_self": true,
      "last_read_at": null,
      "joined_at": "2026-04-17T12:00:00Z"
    },
    {
      "id": 2,
      "user_id": 11,
      "user": 11,
      "username": "contract_tt",
      ...
      "is_self": false,
      ...
    }
  ],
  "primary_recipient": {
    "user_id": 11,
    "full_name": "contract_tt",
    "email": "",
    "phone": "",
    "role": "Tenant",
    "avatar_url": null
  },
  "unread_count": 0,
  "last_message": {
    "id": 1,
    "sender": 11,
    "sender_id": 11,
    "sender_username": "contract_tt",
    "sender_name": "contract_tt",
    "body": "Contract message body",
    "created_at": "2026-04-17T12:00:01Z"
  }
}

Sample GET /api/messaging/participants/ row:

{
  "user_id": 11,
  "full_name": "contract_tt",
  "email": "t@contract.test",
  "phone": "",
  "role": "Tenant",
  "avatar_url": null,
  "is_active": true
}
"""
from django.urls import reverse
from rest_framework.test import APITestCase

from datetime import date

from authentication.models import Role
from property.models import Lease, Property, Unit

from .contract_factories import contract_conversation_with_participants, contract_make_user
from .models import Conversation, ConversationParticipant


PARTICIPANT_STABLE_KEYS = frozenset({
    'id',
    'user_id',
    'user',
    'username',
    'first_name',
    'last_name',
    'full_name',
    'email',
    'phone',
    'role',
    'avatar_url',
    'is_self',
    'last_read_at',
    'joined_at',
})

PRIMARY_RECIPIENT_KEYS = frozenset({
    'user_id', 'full_name', 'email', 'phone', 'role', 'avatar_url',
})

LAST_MESSAGE_KEYS = frozenset({
    'id',
    'sender',
    'sender_id',
    'sender_username',
    'sender_name',
    'body',
    'created_at',
})


def _assert_participant_contract(testcase, p: dict, viewer_id: int):
    missing = PARTICIPANT_STABLE_KEYS - set(p.keys())
    testcase.assertFalse(missing, f'participant missing keys: {sorted(missing)}')
    testcase.assertIsInstance(p['user_id'], int)
    testcase.assertIsInstance(p['user'], int)
    testcase.assertEqual(p['user_id'], p['user'], 'legacy user must mirror user_id')
    testcase.assertIsInstance(p['is_self'], bool)
    testcase.assertEqual(p['is_self'], p['user_id'] == viewer_id)


def _assert_last_message_contract(testcase, lm: dict):
    missing = LAST_MESSAGE_KEYS - set(lm.keys())
    testcase.assertFalse(missing, f'last_message missing keys: {sorted(missing)}')
    testcase.assertIsNotNone(lm['sender'])
    testcase.assertIsInstance(lm['sender'], int)
    testcase.assertIsNotNone(lm['sender_name'])
    testcase.assertIsInstance(lm['sender_name'], str)


class MessagingConversationApiContractTests(APITestCase):
    """Contract for GET /api/messaging/conversations/ and GET .../{id}/."""

    @classmethod
    def setUpTestData(cls):
        cls.landlord, cls.landlord_token = contract_make_user('contract_ll', Role.LANDLORD)
        cls.tenant, cls.tenant_token = contract_make_user('contract_tt', Role.TENANT)
        cls.tenant.email = 't@contract.test'
        cls.tenant.save()
        cls.conv, cls.msg = contract_conversation_with_participants(
            cls.landlord,
            cls.tenant,
            subject='Contract conversation',
            message_body='Contract message body',
            message_sender=cls.tenant,
        )
        cls.conv_empty, _ = contract_conversation_with_participants(
            cls.landlord,
            cls.tenant,
            subject='No messages yet',
            message_body=None,
        )

    def test_list_conversation_participants_schema(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.landlord_token.key}')
        response = self.client.get(reverse('conversation-list-create'))
        self.assertEqual(response.status_code, 200)
        row = next(r for r in response.data if r['id'] == self.conv.id)
        self.assertIn('participants', row)
        self.assertIsInstance(row['participants'], list)
        self.assertGreaterEqual(len(row['participants']), 2)
        for p in row['participants']:
            _assert_participant_contract(self, p, self.landlord.id)

    def test_detail_includes_primary_recipient_object_or_null(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.landlord_token.key}')
        response = self.client.get(reverse('conversation-detail', args=[self.conv.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertIn('primary_recipient', response.data)
        pr = response.data['primary_recipient']
        self.assertIsNotNone(pr)
        self.assertEqual(set(pr.keys()), PRIMARY_RECIPIENT_KEYS)

        d2 = self.client.get(reverse('conversation-detail', args=[self.conv_empty.pk]))
        self.assertEqual(d2.status_code, 200)
        self.assertIn('primary_recipient', d2.data)
        self.assertIsNotNone(d2.data['primary_recipient'])

        solo = Conversation.objects.create(subject='solo thread', created_by=self.landlord)
        ConversationParticipant.objects.create(conversation=solo, user=self.landlord)
        solo_resp = self.client.get(reverse('conversation-detail', args=[solo.pk]))
        self.assertEqual(solo_resp.status_code, 200)
        self.assertIn('primary_recipient', solo_resp.data)
        self.assertIsNone(solo_resp.data['primary_recipient'])

    def test_last_message_schema_when_non_null(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.landlord_token.key}')
        response = self.client.get(reverse('conversation-list-create'))
        self.assertEqual(response.status_code, 200)
        row = next(r for r in response.data if r['id'] == self.conv.id)
        self.assertIsNotNone(row['last_message'])
        _assert_last_message_contract(self, row['last_message'])

        detail = self.client.get(reverse('conversation-detail', args=[self.conv.pk]))
        self.assertIsNotNone(detail.data['last_message'])
        _assert_last_message_contract(self, detail.data['last_message'])

    def test_last_message_null_when_no_messages(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.landlord_token.key}')
        response = self.client.get(reverse('conversation-detail', args=[self.conv_empty.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertIn('last_message', response.data)
        self.assertIsNone(response.data['last_message'])


class MessagingParticipantsDirectoryContractTests(APITestCase):
    """Contract: directory endpoint returns only role-allowed users."""

    @classmethod
    def setUpTestData(cls):
        cls.landlord, cls.landlord_token = contract_make_user('dir_ll', Role.LANDLORD)
        cls.tenant, cls.tenant_token = contract_make_user('dir_tt', Role.TENANT)
        cls.stranger, _ = contract_make_user('dir_stranger', Role.TENANT)
        prop = Property.objects.create(
            name='Dir Prop',
            property_type='apartment',
            owner=cls.landlord,
            created_by=cls.landlord,
        )
        unit = Unit.objects.create(
            property=prop,
            name='U1',
            created_by=cls.landlord,
            is_occupied=True,
        )
        Lease.objects.create(
            unit=unit,
            tenant=cls.tenant,
            start_date=date.today(),
            rent_amount=100,
            is_active=True,
        )

    def test_directory_only_returns_allowed_users_for_landlord(self):
        url = reverse('messaging-participants-lookup')
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.landlord_token.key}')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        ids = {row['user_id'] for row in response.data['results']}
        self.assertIn(self.tenant.id, ids)
        self.assertNotIn(self.stranger.id, ids)
        self.assertNotIn(self.landlord.id, ids)
        for row in response.data['results']:
            self.assertIn('user_id', row)
            self.assertIn('full_name', row)
            self.assertIn('is_active', row)
