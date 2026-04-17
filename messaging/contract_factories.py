"""
Minimal object builders for messaging API contract tests.

Keeps tests fast: no factory_boy; reuse the same users/graph via setUpTestData.
"""
from rest_framework.authtoken.models import Token

from authentication.models import CustomUser, Role

from .models import Conversation, ConversationParticipant, Message


def contract_make_user(username: str, role_name: str, *, password: str = 'contract-pass'):
    role, _ = Role.objects.get_or_create(name=role_name)
    user = CustomUser.objects.create_user(
        username=username,
        password=password,
        role=role,
    )
    token = Token.objects.create(user=user)
    return user, token


def contract_conversation_with_participants(
    creator,
    *other_users,
    subject: str = 'Contract conversation',
    message_body: str | None = 'Contract message body',
    message_sender=None,
):
    """
    Create a conversation with creator + other_users as participants.
    If message_body is not None, creates one message from message_sender (default: first other).
    """
    conv = Conversation.objects.create(subject=subject, created_by=creator)
    ConversationParticipant.objects.create(conversation=conv, user=creator)
    for u in other_users:
        ConversationParticipant.objects.create(conversation=conv, user=u)
    msg = None
    if message_body is not None:
        sender = message_sender or other_users[0]
        msg = Message.objects.create(conversation=conv, sender=sender, body=message_body)
    return conv, msg
