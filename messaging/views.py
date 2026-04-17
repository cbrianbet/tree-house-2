from django.db.models import Prefetch
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiParameter

from authentication.models import CustomUser, Role
from property.models import Property
from .models import Conversation, ConversationParticipant, Message
from .participant_access import (
    apply_search,
    messaging_participants_base_queryset,
    property_directory_user_id_list,
    viewer_may_filter_by_property,
)
from .querysets import conversations_queryset_for_user, get_conversation_for_user
from .serializers import (
    ConversationSerializer,
    MessageSerializer,
    MessagingParticipantLookupSerializer,
)
from .throttling import MessagingParticipantsThrottle


# ── Permission helpers ───────────────────────────────────────────────────────────

def is_participant(user, conversation):
    return conversation.participants.filter(user=user).exists()


# ── Conversations ────────────────────────────────────────────────────────────────

@extend_schema(
    methods=['GET'],
    summary="List conversations for the current user",
    description=(
        'Each row includes `participants` (see ConversationParticipant schema in Swagger components), '
        '`primary_recipient` (user-centric summary or null), and `last_message` '
        '(stable keys when non-null: id, sender, sender_id, sender_username, sender_name, body, created_at). '
        'Field `participants[].user` is deprecated; prefer `user_id`.'
    ),
)
@extend_schema(
    methods=['POST'],
    summary="Create a new conversation",
    examples=[
        OpenApiExample(
            "Create conversation",
            request_only=True,
            value={
                "subject": "About the leaking tap in unit 3",
                "property": 1,
                "participant_ids": [2, 3],
            },
        ),
    ],
)
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def conversation_list_create(request):
    user = request.user

    if request.method == 'GET':
        conversations = conversations_queryset_for_user(user)
        serializer = ConversationSerializer(conversations, many=True, context={'request': request})
        return Response(serializer.data)

    # POST — create conversation
    subject = request.data.get('subject', '')
    property_id = request.data.get('property', None)
    participant_ids = request.data.get('participant_ids', [])

    if not participant_ids:
        return Response(
            {'detail': 'At least one additional participant is required.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    prop = None
    if property_id:
        try:
            prop = Property.objects.get(pk=property_id)
        except Property.DoesNotExist:
            return Response({'detail': 'Property not found.'}, status=status.HTTP_400_BAD_REQUEST)

    conversation = Conversation.objects.create(
        subject=subject,
        created_by=user,
        property=prop,
    )

    # Add creator as participant
    ConversationParticipant.objects.create(conversation=conversation, user=user)

    # Add additional participants
    for uid in participant_ids:
        try:
            participant_user = CustomUser.objects.get(pk=uid)
            ConversationParticipant.objects.get_or_create(
                conversation=conversation,
                user=participant_user,
            )
        except CustomUser.DoesNotExist:
            pass

    from notifications.utils import create_notification
    creator_name = user.get_full_name() or user.username
    for cp in conversation.participants.select_related('user').all():
        if cp.user != user:
            create_notification(
                cp.user,
                'message',
                'New Conversation',
                f"{creator_name} started a conversation: {conversation.subject or '(no subject)'}",
                action_url=f'/api/messaging/conversations/{conversation.pk}/',
            )

    conversation = get_conversation_for_user(user=user, pk=conversation.pk)
    serializer = ConversationSerializer(conversation, context={'request': request})
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@extend_schema(
    methods=['GET'],
    summary="Retrieve a conversation",
    description=(
        'Same payload shape as list rows. `primary_recipient` is null when there is no other participant. '
        'Deprecated: `participants[].user` — use `user_id`.'
    ),
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def conversation_detail(request, pk):
    conversation = conversations_queryset_for_user(request.user).filter(pk=pk).first()
    if conversation is None:
        if Conversation.objects.filter(pk=pk).exists():
            return Response(
                {'detail': 'You are not a participant in this conversation.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

    serializer = ConversationSerializer(conversation, context={'request': request})
    return Response(serializer.data)


# ── Messages ─────────────────────────────────────────────────────────────────────

@extend_schema(
    methods=['GET'],
    summary="List messages in a conversation",
)
@extend_schema(
    methods=['POST'],
    summary="Send a message in a conversation",
    examples=[
        OpenApiExample(
            "Send message",
            request_only=True,
            value={"body": "Hi, I wanted to follow up on the maintenance request."},
        ),
    ],
)
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def message_list_create(request, pk):
    try:
        conversation = Conversation.objects.select_related('created_by').prefetch_related(
            Prefetch(
                'participants',
                queryset=ConversationParticipant.objects.select_related('user', 'user__role'),
            ),
        ).get(pk=pk)
    except Conversation.DoesNotExist:
        return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

    if not is_participant(request.user, conversation):
        return Response({'detail': 'You are not a participant in this conversation.'}, status=status.HTTP_403_FORBIDDEN)

    if request.method == 'GET':
        messages = conversation.messages.select_related('sender').order_by('created_at')
        serializer = MessageSerializer(messages, many=True)
        return Response(serializer.data)

    # POST — send message
    body = request.data.get('body', '').strip()
    if not body:
        return Response({'detail': 'Message body cannot be empty.'}, status=status.HTTP_400_BAD_REQUEST)

    message = Message.objects.create(
        conversation=conversation,
        sender=request.user,
        body=body,
    )

    from notifications.utils import create_notification
    sender_name = request.user.get_full_name() or request.user.username
    for cp in conversation.participants.select_related('user').all():
        if cp.user != request.user:
            create_notification(
                cp.user,
                'message',
                f'New Message from {sender_name}',
                body[:200],
                action_url=f'/api/messaging/conversations/{conversation.pk}/',
            )

    serializer = MessageSerializer(message)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


# ── Participant lookup (compose new conversation) ─────────────────────────────────

@extend_schema(
    methods=['GET'],
    summary='List users you may invite to a new conversation',
    description=(
        'Role-scoped directory for the messaging compose flow. '
        'See `messaging.participant_access` module docstring for the permission matrix.'
    ),
    parameters=[
        OpenApiParameter(
            'search',
            OpenApiTypes.STR,
            description='Case-insensitive match on username, name, email, or phone.',
        ),
        OpenApiParameter(
            'property',
            OpenApiTypes.INT,
            description=(
                'Optional. Restrict to owner, appointed agents, and active tenants on this '
                'property. MovingCompany users cannot use this filter.'
            ),
        ),
        OpenApiParameter(
            'limit',
            OpenApiTypes.INT,
            description='Page size (default 20, max 100).',
        ),
    ],
    examples=[
        OpenApiExample(
            'Example response',
            response_only=True,
            value={
                'results': [
                    {
                        'user_id': 12,
                        'full_name': 'Ann Tenant',
                        'email': 'ann@example.com',
                        'phone': '+254700000000',
                        'role': 'Tenant',
                        'avatar_url': None,
                        'is_active': True,
                    }
                ]
            },
        ),
    ],
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
@throttle_classes([MessagingParticipantsThrottle])
def messaging_participants_lookup(request):
    try:
        limit = int(request.query_params.get('limit', 20))
    except (TypeError, ValueError):
        return Response({'detail': 'Invalid limit.'}, status=status.HTTP_400_BAD_REQUEST)
    limit = max(1, min(limit, 100))

    user = request.user
    qs = messaging_participants_base_queryset(user)

    prop_raw = request.query_params.get('property')
    if prop_raw not in (None, ''):
        if getattr(user, 'role_id', None) and user.role.name == Role.MOVING_COMPANY:
            return Response(
                {'detail': 'The property filter is not supported for your role.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            property_id = int(prop_raw)
        except (TypeError, ValueError):
            return Response({'detail': 'Invalid property id.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            prop = Property.objects.get(pk=property_id)
        except Property.DoesNotExist:
            return Response({'detail': 'Property not found.'}, status=status.HTTP_404_NOT_FOUND)
        if not viewer_may_filter_by_property(user, prop):
            return Response(
                {'detail': 'You do not have access to this property.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        qs = qs.filter(pk__in=property_directory_user_id_list(prop))

    search = request.query_params.get('search', '') or ''
    qs = apply_search(qs, search).order_by('username')[:limit]
    serializer = MessagingParticipantLookupSerializer(qs, many=True)
    return Response({'results': serializer.data})


# ── Mark read ─────────────────────────────────────────────────────────────────────

@extend_schema(
    methods=['POST'],
    summary="Mark a conversation as read for the current user",
    examples=[
        OpenApiExample(
            "Mark read response",
            response_only=True,
            value={"unread_count": 0},
        ),
    ],
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def conversation_mark_read(request, pk):
    try:
        conversation = Conversation.objects.prefetch_related(
            Prefetch(
                'participants',
                queryset=ConversationParticipant.objects.select_related('user', 'user__role'),
            ),
        ).get(pk=pk)
    except Conversation.DoesNotExist:
        return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

    try:
        participant = conversation.participants.get(user=request.user)
    except ConversationParticipant.DoesNotExist:
        return Response({'detail': 'You are not a participant in this conversation.'}, status=status.HTTP_403_FORBIDDEN)

    participant.last_read_at = timezone.now()
    participant.save(update_fields=['last_read_at'])

    # After marking read, unread_count is 0 (no messages after now)
    return Response({'unread_count': 0})
