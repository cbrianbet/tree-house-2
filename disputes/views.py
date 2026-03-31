from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema, OpenApiExample

from authentication.models import Role
from property.models import Lease, PropertyAgent
from .models import Dispute, DisputeMessage
from .serializers import DisputeSerializer, DisputeMessageSerializer


# ── Permission helpers ───────────────────────────────────────────────────────────

def _role_name(user):
    return user.role.name if (user.is_authenticated and hasattr(user, 'role') and user.role) else None


def _is_admin(user):
    return user.is_staff or _role_name(user) == Role.ADMIN


def can_view_dispute(user, dispute):
    """Participant (created_by, property owner) OR Agent assigned to property OR Admin."""
    if _is_admin(user):
        return True
    if dispute.created_by == user:
        return True
    if dispute.property.owner == user:
        return True
    if _role_name(user) == Role.AGENT:
        return PropertyAgent.objects.filter(property=dispute.property, agent=user).exists()
    return False


def can_manage_dispute(user, dispute):
    """Can change status: Landlord (property owner) or Admin only."""
    role_name = _role_name(user)
    if role_name == Role.ADMIN:
        return True
    if dispute.property.owner == user:
        return True
    return False


# ── Disputes list / create ───────────────────────────────────────────────────────

@extend_schema(methods=['GET'], summary="List disputes scoped by role")
@extend_schema(
    methods=['POST'],
    summary="Create a dispute",
    examples=[
        OpenApiExample("Tenant — rent dispute", request_only=True, value={
            "property": 1,
            "unit": 2,
            "dispute_type": "rent",
            "title": "Overcharged rent for March",
            "description": "My rent statement shows an amount higher than what was agreed in the lease.",
        }),
        OpenApiExample("Landlord — noise dispute", request_only=True, value={
            "property": 1,
            "dispute_type": "noise",
            "title": "Persistent noise complaints from unit 4B",
            "description": "Multiple tenants have reported excessive noise coming from unit 4B after 10pm.",
        }),
    ],
)
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def dispute_list_create(request):
    user = request.user
    role_name = _role_name(user)

    if request.method == 'GET':
        if role_name == Role.ARTISAN:
            return Response({'detail': 'Artisans do not have access to disputes.'}, status=status.HTTP_403_FORBIDDEN)

        if role_name == Role.ADMIN:
            qs = Dispute.objects.select_related('property', 'unit', 'created_by', 'resolved_by').all()
        elif role_name == Role.LANDLORD:
            qs = Dispute.objects.filter(property__owner=user).select_related('property', 'unit', 'created_by', 'resolved_by')
        elif role_name == Role.AGENT:
            assigned_ids = PropertyAgent.objects.filter(agent=user).values_list('property_id', flat=True)
            qs = Dispute.objects.filter(property_id__in=assigned_ids).select_related('property', 'unit', 'created_by', 'resolved_by')
        else:
            # Tenant sees own submitted disputes
            qs = Dispute.objects.filter(created_by=user).select_related('property', 'unit', 'created_by', 'resolved_by')

        serializer = DisputeSerializer(qs, many=True)
        return Response(serializer.data)

    elif request.method == 'POST':
        # Agents and Artisans cannot create disputes
        if role_name in (Role.AGENT, Role.ARTISAN):
            return Response({'detail': 'Agents and artisans cannot submit disputes.'}, status=status.HTTP_403_FORBIDDEN)

        serializer = DisputeSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        prop = serializer.validated_data['property']
        unit = serializer.validated_data.get('unit')

        # Unit (if provided) must belong to the property
        if unit and unit.property_id != prop.id:
            return Response(
                {'detail': 'The specified unit does not belong to this property.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Landlord must own the property
        if role_name == Role.LANDLORD:
            if prop.owner != user:
                return Response(
                    {'detail': 'You can only submit disputes for properties you own.'},
                    status=status.HTTP_403_FORBIDDEN,
                )
        else:
            # Tenant must have an active lease on the property
            has_lease = Lease.objects.filter(
                unit__property=prop, tenant=user, is_active=True
            ).exists()
            if not has_lease:
                return Response(
                    {'detail': 'You do not have an active lease on this property.'},
                    status=status.HTTP_403_FORBIDDEN,
                )

        dispute = serializer.save(created_by=user, status='open')
        from notifications.utils import create_notification
        create_notification(
            dispute.property.owner,
            'dispute',
            'New Dispute Filed',
            f"A dispute has been filed on your property '{dispute.property.name}': {dispute.title}",
            action_url=f'/api/disputes/{dispute.pk}/',
        )
        return Response(DisputeSerializer(dispute).data, status=status.HTTP_201_CREATED)


# ── Dispute detail ───────────────────────────────────────────────────────────────

@extend_schema(methods=['GET'], summary="Retrieve a dispute")
@extend_schema(
    methods=['PATCH'],
    summary="Update dispute status",
    examples=[
        OpenApiExample("Move to under_review (landlord/admin)", request_only=True, value={"status": "under_review"}),
        OpenApiExample("Resolve (admin only)", request_only=True, value={"status": "resolved"}),
        OpenApiExample("Close (creator only)", request_only=True, value={"status": "closed"}),
    ],
)
@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated])
def dispute_detail(request, pk):
    try:
        dispute = Dispute.objects.select_related('property', 'unit', 'created_by', 'resolved_by').get(pk=pk)
    except Dispute.DoesNotExist:
        return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

    if not can_view_dispute(request.user, dispute):
        return Response({'detail': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)

    if request.method == 'GET':
        return Response(DisputeSerializer(dispute).data)

    elif request.method == 'PATCH':
        new_status = request.data.get('status')
        if not new_status:
            return Response({'detail': 'No status provided.'}, status=status.HTTP_400_BAD_REQUEST)

        error = _validate_status_transition(request.user, dispute, new_status)
        if error:
            return Response({'detail': error}, status=status.HTTP_400_BAD_REQUEST)

        dispute.status = new_status
        if new_status == 'resolved':
            dispute.resolved_by = request.user
            dispute.resolved_at = timezone.now()
        dispute.save()

        from notifications.utils import create_notification
        create_notification(
            dispute.created_by,
            'dispute',
            'Dispute Status Updated',
            f"Your dispute '{dispute.title}' is now {new_status.replace('_', ' ')}.",
            action_url=f'/api/disputes/{dispute.pk}/',
        )
        return Response(DisputeSerializer(dispute).data)


def _validate_status_transition(user, dispute, new_status):
    """Return an error string if the transition is invalid, else None."""
    current = dispute.status
    role_name = _role_name(user)

    # Resolved/closed disputes cannot be reopened
    if current in ('resolved', 'closed'):
        return f'Dispute is already {current} and cannot be changed.'

    if new_status == 'under_review':
        # open → under_review: Landlord (property owner) or Admin only
        if role_name != Role.ADMIN and dispute.property.owner != user:
            return 'Only the property owner or admin can move a dispute to under_review.'
        if current != 'open':
            return f'Cannot move to under_review from {current}.'

    elif new_status == 'resolved':
        # under_review → resolved: Admin only
        if role_name != Role.ADMIN:
            return 'Only an admin can mark a dispute as resolved.'
        if current != 'under_review':
            return f'Cannot resolve from {current}. Dispute must be under_review first.'

    elif new_status == 'closed':
        # open or under_review → closed: creator only
        if dispute.created_by != user:
            return 'Only the dispute creator can close the dispute.'
        if current not in ('open', 'under_review'):
            return f'Cannot close from {current}.'

    else:
        return f'Invalid status: {new_status}.'

    return None


# ── Dispute messages ─────────────────────────────────────────────────────────────

@extend_schema(methods=['GET'], summary="List messages for a dispute")
@extend_schema(
    methods=['POST'],
    summary="Post a message on a dispute",
    examples=[
        OpenApiExample("Post message", request_only=True, value={
            "body": "I have attached the original signed lease agreement for reference.",
        }),
    ],
)
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def dispute_message_list_create(request, pk):
    try:
        dispute = Dispute.objects.select_related('property', 'created_by').get(pk=pk)
    except Dispute.DoesNotExist:
        return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

    if not can_view_dispute(request.user, dispute):
        return Response({'detail': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)

    if request.method == 'GET':
        messages = dispute.messages.select_related('sender').all()
        return Response(DisputeMessageSerializer(messages, many=True).data)

    elif request.method == 'POST':
        serializer = DisputeMessageSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(dispute=dispute, sender=request.user)
            from notifications.utils import create_notification
            sender_name = request.user.get_full_name() or request.user.username
            participants = {dispute.created_by, dispute.property.owner}
            for pa in PropertyAgent.objects.filter(property=dispute.property).select_related('agent'):
                participants.add(pa.agent)
            for participant in participants:
                if participant != request.user:
                    create_notification(
                        participant,
                        'dispute',
                        'New Message on Dispute',
                        f"{sender_name} posted a message on dispute '{dispute.title}'.",
                        action_url=f'/api/disputes/{dispute.pk}/',
                    )
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
