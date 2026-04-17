"""
Messaging serializers.

Frontend deprecation (participants on conversation payloads):
- **Now–Q4 2026:** `participants[].user` remains populated (same int as `user_id`); OpenAPI marks it deprecated.
- **Target removal (not before 2027-01):** drop `user` once all clients use `user_id`; coordinate with mobile/web release train.
"""
from rest_framework import serializers
from drf_spectacular.utils import OpenApiExample, extend_schema_serializer

from authentication.models import CustomUser
from .models import Conversation, ConversationParticipant, Message


def _user_role_name(user):
    if not user.role_id:
        return None
    role = user.role
    if role is None:
        return None
    return role.name


def primary_recipient_blob(user):
    """User-centric display payload for primary_recipient (no participant row id)."""
    return {
        'user_id': user.id,
        'full_name': user.get_full_name().strip() or user.username,
        'email': user.email or '',
        'phone': user.phone or '',
        'role': _user_role_name(user),
        'avatar_url': None,
    }


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            'Participant directory row',
            value={
                'user_id': 42,
                'full_name': 'Sam Tenant',
                'email': 'sam@example.com',
                'phone': '+1555000100',
                'role': 'Tenant',
                'avatar_url': None,
                'is_active': True,
            },
            response_only=True,
        ),
    ],
)
class MessagingParticipantLookupSerializer(serializers.ModelSerializer):
    """Row for GET /api/messaging/participants/ (compose conversation picker)."""

    user_id = serializers.IntegerField(source='id', read_only=True)
    full_name = serializers.SerializerMethodField()
    role = serializers.SerializerMethodField()
    avatar_url = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = [
            'user_id',
            'full_name',
            'email',
            'phone',
            'role',
            'avatar_url',
            'is_active',
        ]

    def get_full_name(self, obj):
        return obj.get_full_name().strip() or obj.username

    def get_role(self, obj):
        return _user_role_name(obj)

    def get_avatar_url(self, obj):
        return None


@extend_schema_serializer(
    deprecate_fields=('user',),
    examples=[
        OpenApiExample(
            'Conversation participant',
            value={
                'id': 9,
                'user_id': 42,
                'user': 42,
                'username': 'sam_t',
                'first_name': 'Sam',
                'last_name': 'Tenant',
                'full_name': 'Sam Tenant',
                'email': 'sam@example.com',
                'phone': '+1555000100',
                'role': 'Tenant',
                'avatar_url': None,
                'is_self': False,
                'last_read_at': None,
                'joined_at': '2026-04-17T12:00:00Z',
            },
            response_only=True,
        ),
    ],
)
class ConversationParticipantSerializer(serializers.ModelSerializer):
    """
    Participant row + normalized user identity for FE.

    OpenAPI: ``user`` is deprecated (alias of ``user_id``); new clients should use ``user_id`` only.
    """
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    user = serializers.IntegerField(
        source='user.id',
        read_only=True,
        help_text='Deprecated: same integer as user_id. Prefer user_id.',
    )
    username = serializers.CharField(source='user.username', read_only=True)
    first_name = serializers.CharField(source='user.first_name', read_only=True)
    last_name = serializers.CharField(source='user.last_name', read_only=True)
    full_name = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()
    phone = serializers.SerializerMethodField()
    role = serializers.SerializerMethodField()
    avatar_url = serializers.SerializerMethodField()
    is_self = serializers.SerializerMethodField()

    class Meta:
        model = ConversationParticipant
        fields = [
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
        ]

    def get_full_name(self, obj):
        u = obj.user
        return u.get_full_name().strip() or u.username

    def get_email(self, obj):
        return obj.user.email or ''

    def get_phone(self, obj):
        return obj.user.phone or ''

    def get_role(self, obj):
        return _user_role_name(obj.user)

    def get_avatar_url(self, obj):
        return None

    def get_is_self(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        return obj.user_id == request.user.id


@extend_schema_serializer(
    examples=[
        OpenApiExample(
            'Conversation with last_message',
            value={
                'id': 1,
                'property': None,
                'subject': 'Maintenance follow-up',
                'created_by': 10,
                'created_at': '2026-04-17T12:00:00Z',
                'participants': [],
                'primary_recipient': {
                    'user_id': 11,
                    'full_name': 'Sam Tenant',
                    'email': 'sam@example.com',
                    'phone': '',
                    'role': 'Tenant',
                    'avatar_url': None,
                },
                'unread_count': 0,
                'last_message': {
                    'id': 99,
                    'sender': 11,
                    'sender_id': 11,
                    'sender_username': 'sam_t',
                    'sender_name': 'Sam Tenant',
                    'body': 'Thanks!',
                    'created_at': '2026-04-17T12:05:00Z',
                },
            },
            response_only=True,
        ),
    ],
)
class ConversationSerializer(serializers.ModelSerializer):
    participants = ConversationParticipantSerializer(many=True, read_only=True)
    primary_recipient = serializers.SerializerMethodField(
        help_text='First other participant (by participant row id); null if none.',
    )
    unread_count = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField(
        help_text='Latest message summary; null if no messages. When set, includes sender, sender_name, body, created_at.',
    )

    class Meta:
        model = Conversation
        fields = [
            'id',
            'property',
            'subject',
            'created_by',
            'created_at',
            'participants',
            'primary_recipient',
            'unread_count',
            'last_message',
        ]
        read_only_fields = ['id', 'created_by', 'created_at']

    def get_primary_recipient(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return None
        # Prefetch uses order_by('id') for deterministic "first other" in group chats.
        for p in obj.participants.all():
            if p.user_id != request.user.id:
                return primary_recipient_blob(p.user)
        return None

    def get_unread_count(self, obj):
        annotated = getattr(obj, '_unread_count', None)
        if annotated is not None:
            return annotated
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return 0
        user = request.user
        try:
            participant = obj.participants.get(user=user)
        except ConversationParticipant.DoesNotExist:
            return 0
        last_read = participant.last_read_at
        if last_read is None:
            return obj.messages.count()
        return obj.messages.filter(created_at__gt=last_read).count()

    def get_last_message(self, obj):
        lm_id = getattr(obj, '_lm_id', None)
        if lm_id is not None:
            sender_id = getattr(obj, '_lm_sender_id', None)
            sender_name = getattr(obj, '_lm_sender_name', None) or ''
            sender_username = getattr(obj, '_lm_sender_username', None) or ''
            return {
                'id': lm_id,
                'sender': sender_id,
                'sender_id': sender_id,
                'sender_username': sender_username,
                'sender_name': sender_name,
                'body': getattr(obj, '_lm_body', None),
                'created_at': getattr(obj, '_lm_created_at', None),
            }
        last = obj.messages.order_by('-created_at').select_related('sender').first()
        if last is None:
            return None
        sender_name = (
            f'{last.sender.first_name} {last.sender.last_name}'.strip()
            or last.sender.username
        )
        return {
            'id': last.id,
            'sender': last.sender_id,
            'sender_id': last.sender_id,
            'sender_username': last.sender.username,
            'sender_name': sender_name,
            'body': last.body,
            'created_at': last.created_at,
        }


class MessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = ['id', 'conversation', 'sender', 'sender_name', 'body', 'created_at']
        read_only_fields = ['id', 'conversation', 'sender', 'created_at']

    def get_sender_name(self, obj):
        return f"{obj.sender.first_name} {obj.sender.last_name}".strip() or obj.sender.username
