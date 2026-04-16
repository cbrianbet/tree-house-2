from django.utils import timezone
from django.db.models import Count, Q
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema, OpenApiExample

from authentication.models import Role
from property.models import PropertyAgent, Lease
from property.views import is_admin, is_landlord, is_agent_for
from .models import MaintenanceRequest, MaintenanceBid, MaintenanceNote, MaintenanceImage
from .serializers import (
    MaintenanceRequestSerializer, MaintenanceBidSerializer,
    MaintenanceNoteSerializer, MaintenanceImageSerializer, MaintenanceTimelineEventSerializer,
)


# ── Permission helpers ──────────────────────────────────────────────────────────

def is_artisan(user):
    return user.is_authenticated and hasattr(user, 'role') and user.role.name == Role.ARTISAN


def _display_name(user):
    if not user:
        return None
    full_name = f"{user.first_name} {user.last_name}".strip()
    return full_name or user.username


def can_view_request(user, req):
    """Admin, property owner, assigned agent, submitter, or assigned artisan."""
    return (
        is_admin(user)
        or req.property.owner == user
        or is_agent_for(user, req.property)
        or req.submitted_by == user
        or req.assigned_to == user
    )


def can_manage_request(user, req):
    """Submitter or admin can change status, accept bids, mark complete."""
    return is_admin(user) or req.submitted_by == user


# ── Requests ────────────────────────────────────────────────────────────────────

@extend_schema(methods=['GET'], summary="List maintenance requests")
@extend_schema(
    methods=['POST'],
    summary="Submit a maintenance request",
    examples=[
        OpenApiExample("Tenant — unit request", request_only=True, value={
            "property": 1,
            "unit": 2,
            "title": "Leaking kitchen tap",
            "description": "The kitchen tap has been dripping for 3 days.",
            "category": "plumbing",
            "priority": "medium",
        }),
        OpenApiExample("Landlord — common area", request_only=True, value={
            "property": 1,
            "title": "Broken gate motor",
            "description": "Main entrance gate motor needs replacement.",
            "category": "electrical",
            "priority": "high",
        }),
    ],
)
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def request_list_create(request):
    user = request.user

    if request.method == 'GET':
        if is_admin(user):
            qs = MaintenanceRequest.objects.select_related('property', 'unit', 'submitted_by').all()
        elif is_landlord(user):
            qs = MaintenanceRequest.objects.filter(property__owner=user)
        elif hasattr(user, 'role') and user.role.name == Role.AGENT:
            assigned_ids = PropertyAgent.objects.filter(agent=user).values_list('property_id', flat=True)
            qs = MaintenanceRequest.objects.filter(property_id__in=assigned_ids)
        elif is_artisan(user):
            # Artisans see open requests matching their trade
            try:
                trade = user.artisan_profile.trade
                qs = MaintenanceRequest.objects.filter(status='open', category=trade)
            except Exception:
                qs = MaintenanceRequest.objects.filter(status='open')
        else:
            # Tenant sees their own submitted requests
            qs = MaintenanceRequest.objects.filter(submitted_by=user)

        serializer = MaintenanceRequestSerializer(qs, many=True)
        return Response(serializer.data)

    elif request.method == 'POST':
        if is_artisan(user) or (hasattr(user, 'role') and user.role.name == Role.AGENT):
            return Response({'detail': 'Agents and artisans cannot submit maintenance requests.'}, status=status.HTTP_403_FORBIDDEN)

        serializer = MaintenanceRequestSerializer(data=request.data)
        if serializer.is_valid():
            prop = serializer.validated_data['property']
            unit = serializer.validated_data.get('unit')

            # Unit must belong to the specified property
            if unit and unit.property_id != prop.id:
                return Response({'detail': 'The specified unit does not belong to this property.'}, status=status.HTTP_400_BAD_REQUEST)

            # Landlord must own the property
            if is_landlord(user) and prop.owner != user:
                return Response({'detail': 'You can only submit requests for properties you own.'}, status=status.HTTP_403_FORBIDDEN)

            # Tenant must have an active lease on the unit (or any unit in the property for common-area requests)
            if not is_landlord(user) and not is_admin(user):
                if unit:
                    has_access = Lease.objects.filter(unit=unit, tenant=user, is_active=True).exists()
                else:
                    has_access = Lease.objects.filter(unit__property=prop, tenant=user, is_active=True).exists()
                if not has_access:
                    return Response({'detail': 'You do not have an active lease on this property.'}, status=status.HTTP_403_FORBIDDEN)

            serializer.save(submitted_by=user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(methods=['GET'], summary="Get maintenance request detail")
@extend_schema(
    methods=['PUT'],
    summary="Update maintenance request status",
    examples=[
        OpenApiExample("Open for bidding (landlord/admin)", request_only=True, value={"status": "open"}),
        OpenApiExample("Mark completed (submitter)", request_only=True, value={"status": "completed"}),
        OpenApiExample("Artisan starts work", request_only=True, value={"status": "in_progress"}),
        OpenApiExample("Cancel (submitter)", request_only=True, value={"status": "cancelled"}),
    ],
)
@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated])
def request_detail(request, pk):
    try:
        req = MaintenanceRequest.objects.select_related('property', 'unit', 'submitted_by', 'assigned_to').get(pk=pk)
    except MaintenanceRequest.DoesNotExist:
        return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

    if not can_view_request(request.user, req):
        return Response({'detail': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)

    if request.method == 'GET':
        return Response(MaintenanceRequestSerializer(req).data)

    elif request.method == 'PUT':
        new_status = request.data.get('status')
        user = request.user

        if new_status:
            error = _validate_status_transition(user, req, new_status)
            if error:
                return Response({'detail': error}, status=status.HTTP_403_FORBIDDEN)

            if new_status == 'completed':
                req.resolved_at = timezone.now()
            req.status = new_status
            req.save()

            # Auto-create expense from accepted bid when work is confirmed complete
            if new_status == 'completed':
                from billing.models import Expense
                accepted_bid = req.bids.filter(status='accepted').first()
                if accepted_bid:
                    Expense.objects.create(
                        property=req.property,
                        unit=req.unit,
                        maintenance_request=req,
                        category='maintenance',
                        amount=accepted_bid.proposed_price,
                        description=f"Maintenance completed: {req.title}",
                        date=timezone.now().date(),
                        recorded_by=user,
                    )

            return Response(MaintenanceRequestSerializer(req).data)

        # Non-status fields (priority, title, etc.) — submitter or admin only
        if not can_manage_request(user, req):
            return Response({'detail': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)

        serializer = MaintenanceRequestSerializer(req, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


def _validate_status_transition(user, req, new_status):
    """Return an error string if the transition is not allowed, else None."""
    current = req.status

    # Admin bypasses all checks
    if is_admin(user):
        return None

    # submitted → open: landlord (property owner) only
    if new_status == 'open':
        if req.property.owner != user:
            return 'Only the property owner can open a request for bidding.'
        if current != 'submitted':
            return f'Cannot move to open from {current}.'

    # assigned → in_progress: assigned artisan only
    elif new_status == 'in_progress':
        if req.assigned_to != user:
            return 'Only the assigned artisan can mark this as in progress.'
        if current != 'assigned':
            return f'Cannot move to in_progress from {current}.'

    # in_progress → completed: submitter only
    elif new_status == 'completed':
        if req.submitted_by != user:
            return 'Only the request submitter can mark it as completed.'
        if current != 'in_progress':
            return f'Cannot mark complete from {current}.'

    # any → cancelled: submitter (only when submitted/open)
    elif new_status == 'cancelled':
        if req.submitted_by != user:
            return 'Only the submitter can cancel a request.'
        if current not in ('submitted', 'open'):
            return f'Cannot cancel from {current}.'

    # any → rejected: landlord/property owner only
    elif new_status == 'rejected':
        if req.property.owner != user:
            return 'Only the property owner can reject a request.'

    else:
        return f'Invalid status: {new_status}.'

    return None


# ── Bids ────────────────────────────────────────────────────────────────────────

@extend_schema(methods=['GET'], summary="List bids for a request")
@extend_schema(
    methods=['POST'],
    summary="Place a bid on a maintenance request (artisans only)",
    examples=[
        OpenApiExample("Place bid", request_only=True, value={
            "proposed_price": "8500.00",
            "message": "I can fix this within 2 days using quality materials.",
        })
    ],
)
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def bid_list_create(request, pk):
    try:
        req = MaintenanceRequest.objects.select_related('property').get(pk=pk)
    except MaintenanceRequest.DoesNotExist:
        return Response({'detail': 'Request not found.'}, status=status.HTTP_404_NOT_FOUND)

    user = request.user

    if request.method == 'GET':
        # Artisans see only their own bid; others see all
        if is_artisan(user):
            bids = req.bids.select_related('artisan__artisan_profile').filter(artisan=user).annotate(
                artisan_completed_jobs=Count(
                    'artisan__assigned_maintenance',
                    filter=Q(artisan__assigned_maintenance__status='completed'),
                    distinct=True,
                )
            )
        elif can_view_request(user, req):
            bids = req.bids.select_related('artisan__artisan_profile').all().annotate(
                artisan_completed_jobs=Count(
                    'artisan__assigned_maintenance',
                    filter=Q(artisan__assigned_maintenance__status='completed'),
                    distinct=True,
                )
            )
        else:
            return Response({'detail': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)
        return Response(MaintenanceBidSerializer(bids, many=True).data)

    elif request.method == 'POST':
        if not is_artisan(user):
            return Response({'detail': 'Only artisans can place bids.'}, status=status.HTTP_403_FORBIDDEN)
        if req.status != 'open':
            return Response({'detail': 'Bids can only be placed on open requests.'}, status=status.HTTP_400_BAD_REQUEST)
        if req.bids.filter(artisan=user).exists():
            return Response({'detail': 'You have already placed a bid on this request.'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = MaintenanceBidSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(request=req, artisan=user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    methods=['PUT'],
    summary="Accept or reject a bid (submitter only)",
    examples=[
        OpenApiExample("Accept bid", request_only=True, value={"status": "accepted"}),
        OpenApiExample("Reject bid", request_only=True, value={"status": "rejected"}),
    ],
)
@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def bid_detail(request, pk, bid_id):
    try:
        req = MaintenanceRequest.objects.select_related('property').get(pk=pk)
    except MaintenanceRequest.DoesNotExist:
        return Response({'detail': 'Request not found.'}, status=status.HTTP_404_NOT_FOUND)

    try:
        bid = MaintenanceBid.objects.get(pk=bid_id, request=req)
    except MaintenanceBid.DoesNotExist:
        return Response({'detail': 'Bid not found.'}, status=status.HTTP_404_NOT_FOUND)

    if not can_manage_request(request.user, req):
        return Response({'detail': 'Only the request submitter can accept or reject bids.'}, status=status.HTTP_403_FORBIDDEN)

    new_status = request.data.get('status')
    if new_status not in ('accepted', 'rejected'):
        return Response({'detail': 'status must be "accepted" or "rejected".'}, status=status.HTTP_400_BAD_REQUEST)

    if new_status == 'accepted':
        if req.status != 'open':
            return Response({'detail': 'Request must be open to accept a bid.'}, status=status.HTTP_400_BAD_REQUEST)
        # Accept this bid, reject all others
        req.bids.exclude(pk=bid_id).update(status='rejected')
        bid.status = 'accepted'
        bid.save()
        req.assigned_to = bid.artisan
        req.status = 'assigned'
        req.save()
    else:
        bid.status = 'rejected'
        bid.save()

    return Response(MaintenanceBidSerializer(bid).data)


@extend_schema(
    methods=['GET'],
    summary="Get activity timeline for a maintenance request",
    responses=MaintenanceTimelineEventSerializer(many=True),
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def request_timeline(request, pk):
    try:
        req = MaintenanceRequest.objects.select_related(
            'property',
            'submitted_by',
            'assigned_to',
        ).get(pk=pk)
    except MaintenanceRequest.DoesNotExist:
        return Response({'detail': 'Request not found.'}, status=status.HTTP_404_NOT_FOUND)

    if not can_view_request(request.user, req):
        return Response({'detail': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)

    events = [{
        'event_type': 'request_submitted',
        'description': f"Maintenance request submitted: {req.title}.",
        'actor': _display_name(req.submitted_by),
        'created_at': req.created_at,
    }]

    bids = req.bids.select_related('artisan').all()
    for bid in bids:
        events.append({
            'event_type': 'bid_submitted',
            'description': f"{_display_name(bid.artisan)} submitted a bid of KES {bid.proposed_price}.",
            'actor': _display_name(bid.artisan),
            'created_at': bid.created_at,
        })
        if bid.status in ('accepted', 'rejected'):
            events.append({
                'event_type': f"bid_{bid.status}",
                'description': f"Bid by {_display_name(bid.artisan)} was {bid.status}.",
                'actor': _display_name(req.submitted_by),
                'created_at': req.updated_at,
            })

    notes = req.notes.select_related('author').all()
    for note in notes:
        events.append({
            'event_type': 'note_added',
            'description': note.note,
            'actor': _display_name(note.author),
            'created_at': note.created_at,
        })

    if req.status != 'submitted':
        events.append({
            'event_type': 'status_changed',
            'description': f"Request status is now {req.status.replace('_', ' ')}.",
            'actor': _display_name(req.assigned_to) if req.status == 'in_progress' else _display_name(req.submitted_by),
            'created_at': req.resolved_at or req.updated_at,
        })

    from notifications.models import Notification
    request_path = f"/maintenance/requests/{req.id}"
    notifications = Notification.objects.filter(
        notification_type='maintenance',
        action_url__icontains=request_path,
    ).select_related('user')
    for notif in notifications:
        events.append({
            'event_type': 'notification_sent',
            'description': f"{notif.title}: {notif.body}",
            'actor': _display_name(notif.user),
            'created_at': notif.created_at,
        })

    events.sort(key=lambda event: event['created_at'])
    return Response(MaintenanceTimelineEventSerializer(events, many=True).data)


# ── Notes ───────────────────────────────────────────────────────────────────────

@extend_schema(methods=['GET'], summary="List notes for a request")
@extend_schema(
    methods=['POST'],
    summary="Add a note to a request",
    examples=[
        OpenApiExample("Add note", request_only=True, value={"note": "Artisan confirmed arrival for Tuesday 10am."})
    ],
)
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def note_list_create(request, pk):
    try:
        req = MaintenanceRequest.objects.select_related('property').get(pk=pk)
    except MaintenanceRequest.DoesNotExist:
        return Response({'detail': 'Request not found.'}, status=status.HTTP_404_NOT_FOUND)

    if not can_view_request(request.user, req):
        return Response({'detail': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)

    if request.method == 'GET':
        notes = req.notes.select_related('author').all()
        return Response(MaintenanceNoteSerializer(notes, many=True).data)

    elif request.method == 'POST':
        serializer = MaintenanceNoteSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(request=req, author=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ── Images ──────────────────────────────────────────────────────────────────────

@extend_schema(methods=['GET'], summary="List images for a request")
@extend_schema(methods=['POST'], summary="Upload an image for a request")
@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def image_list_create(request, pk):
    try:
        req = MaintenanceRequest.objects.select_related('property').get(pk=pk)
    except MaintenanceRequest.DoesNotExist:
        return Response({'detail': 'Request not found.'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        images = req.images.all()
        return Response(MaintenanceImageSerializer(images, many=True).data)

    elif request.method == 'POST':
        if not request.user.is_authenticated:
            return Response({'detail': 'Authentication required.'}, status=status.HTTP_401_UNAUTHORIZED)
        if not can_view_request(request.user, req):
            return Response({'detail': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)
        serializer = MaintenanceImageSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(request=req, uploaded_by=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
