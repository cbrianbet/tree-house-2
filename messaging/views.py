from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema, OpenApiExample

from authentication.models import CustomUser
from .models import Conversation, ConversationParticipant, Message
from .serializers import ConversationSerializer, MessageSerializer


# ── Permission helpers ───────────────────────────────────────────────────────────

def is_participant(user, conversation):
    return conversation.participants.filter(user=user).exists()


# ── Conversations ────────────────────────────────────────────────────────────────

@extend_schema(
    methods=['GET'],
    summary="List conversations for the current user",
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
        conversations = (
            Conversation.objects
            .filter(participants__user=user)
            .select_related('created_by', 'property')
            .prefetch_related('participants__user', 'messages')
            .order_by('-messages__created_at')
            .distinct()
        )
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

    conversation = Conversation.objects.create(
        subject=subject,
        created_by=user,
        property_id=property_id if property_id else None,
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

    # TODO: trigger notification after merge — from notifications.utils import create_notification

    serializer = ConversationSerializer(conversation, context={'request': request})
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@extend_schema(
    methods=['GET'],
    summary="Retrieve a conversation",
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def conversation_detail(request, pk):
    try:
        conversation = (
            Conversation.objects
            .select_related('created_by', 'property')
            .prefetch_related('participants__user', 'messages')
            .get(pk=pk)
        )
    except Conversation.DoesNotExist:
        return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

    if not is_participant(request.user, conversation):
        return Response({'detail': 'You are not a participant in this conversation.'}, status=status.HTTP_403_FORBIDDEN)

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
        conversation = Conversation.objects.select_related('created_by').prefetch_related('participants__user').get(pk=pk)
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

    # TODO: trigger notification after merge — from notifications.utils import create_notification

    serializer = MessageSerializer(message)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


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
        conversation = Conversation.objects.prefetch_related('participants__user').get(pk=pk)
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
