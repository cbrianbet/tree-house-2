from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from .models import Notification
from .serializers import NotificationSerializer


# ── Notification list ────────────────────────────────────────────────────────

@extend_schema(
    methods=['GET'],
    summary="List own notifications",
    parameters=[
        OpenApiParameter(
            name='unread',
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            description='Filter to unread notifications only. Pass "true" to filter.',
            required=False,
        ),
    ],
    responses={200: NotificationSerializer(many=True)},
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def notification_list(request):
    """Return all notifications for the authenticated user, optionally filtered to unread."""
    qs = Notification.objects.select_related('user').filter(user=request.user)
    if request.query_params.get('unread', '').lower() == 'true':
        qs = qs.filter(is_read=False)
    serializer = NotificationSerializer(qs, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


# ── Mark single notification read ────────────────────────────────────────────

@extend_schema(
    methods=['POST'],
    summary="Mark a notification as read",
    responses={200: NotificationSerializer},
    examples=[
        OpenApiExample(
            "Mark read response",
            response_only=True,
            value={
                "id": 1,
                "notification_type": "payment",
                "title": "Payment received",
                "body": "Your payment of KES 10,000 was received.",
                "action_url": "/invoices/42/",
                "is_read": True,
                "created_at": "2026-03-30T10:00:00Z",
            },
        ),
    ],
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def notification_mark_read(request, pk):
    """Mark a single notification as read. Returns 404 if not found or not owned by requester."""
    try:
        notification = Notification.objects.get(pk=pk, user=request.user)
    except Notification.DoesNotExist:
        return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

    notification.is_read = True
    notification.save(update_fields=['is_read'])
    serializer = NotificationSerializer(notification)
    return Response(serializer.data, status=status.HTTP_200_OK)


# ── Mark all notifications read ───────────────────────────────────────────────

@extend_schema(
    methods=['POST'],
    summary="Mark all notifications as read",
    responses={200: {'type': 'object', 'properties': {'detail': {'type': 'string'}}}},
    examples=[
        OpenApiExample(
            "Read-all response",
            response_only=True,
            value={"detail": "All notifications marked as read."},
        ),
    ],
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def notification_read_all(request):
    """Mark all of the authenticated user's notifications as read."""
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return Response({'detail': 'All notifications marked as read.'}, status=status.HTTP_200_OK)
