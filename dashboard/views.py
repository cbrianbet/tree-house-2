from datetime import date, timedelta
from decimal import Decimal

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema, OpenApiExample
from django.db.models import Sum, Q

from authentication.models import CustomUser, Role
from .models import RoleChangeLog
from .serializers import AdminUserSerializer, AdminUserUpdateSerializer, RoleChangeLogSerializer


# ---------------------------------------------------------------------------
# Permission helpers
# ---------------------------------------------------------------------------

def _is_admin(user):
    return user.is_staff

def _is_tenant(user):
    return user.role and user.role.name == Role.TENANT

def _is_artisan(user):
    return user.role and user.role.name == Role.ARTISAN

def _is_agent(user):
    return user.role and user.role.name == Role.AGENT

def _is_moving_company(user):
    return user.role and user.role.name == Role.MOVING_COMPANY


# ---------------------------------------------------------------------------
# Admin — System Overview
# ---------------------------------------------------------------------------

@extend_schema(
    methods=['GET'],
    summary="Admin system overview — platform-wide metrics",
    examples=[
        OpenApiExample("Overview response", value={
            "users": {"total": 150, "by_role": {"Tenant": 80, "Landlord": 30}, "new_last_30_days": 12},
            "properties": {"total": 45, "total_units": 320, "occupied": 275, "vacant": 45, "occupancy_rate": "85.9%"},
            "billing": {"revenue_this_month": "1250000.00", "outstanding": "450000.00", "overdue_invoices": 8},
            "maintenance": {"submitted": 5, "open": 12, "assigned": 8, "in_progress": 6, "completed_this_month": 15},
            "disputes": {"open": 3, "under_review": 2},
            "moving": {"total_companies": 5, "pending_bookings": 10, "completed_this_month": 8},
        })
    ],
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def admin_overview(request):
    if not _is_admin(request.user):
        return Response({'detail': 'Admin access required.'}, status=status.HTTP_403_FORBIDDEN)

    from property.models import Property, Unit
    from billing.models import Invoice, Payment
    from maintenance.models import MaintenanceRequest
    from disputes.models import Dispute
    from moving.models import MovingBooking
    from authentication.models import MovingCompanyProfile

    today = date.today()
    thirty_days_ago = today - timedelta(days=30)
    year, month = today.year, today.month

    # ── Users ─────────────────────────────────────────────────────────────────
    all_users = CustomUser.objects.select_related('role').filter(is_staff=False)
    by_role = {}
    for u in all_users:
        role_name = u.role.name if u.role else 'Unknown'
        by_role[role_name] = by_role.get(role_name, 0) + 1

    new_users = CustomUser.objects.filter(date_joined__date__gte=thirty_days_ago).count()

    # ── Properties ────────────────────────────────────────────────────────────
    total_properties = Property.objects.count()
    total_units = Unit.objects.count()
    occupied = Unit.objects.filter(is_occupied=True).count()
    vacant = total_units - occupied
    occupancy_rate = f"{(occupied / total_units * 100):.1f}%" if total_units else "0%"

    # ── Billing ───────────────────────────────────────────────────────────────
    revenue = Payment.objects.filter(
        status='completed', paid_at__year=year, paid_at__month=month
    ).aggregate(t=Sum('amount'))['t'] or Decimal('0')

    outstanding = Invoice.objects.filter(
        status__in=['pending', 'partial', 'overdue']
    ).aggregate(t=Sum('total_amount'))['t'] or Decimal('0')

    overdue_invoices = Invoice.objects.filter(status='overdue').count()

    # ── Maintenance ───────────────────────────────────────────────────────────
    maint = MaintenanceRequest.objects
    completed_this_month = maint.filter(
        status='completed', resolved_at__year=year, resolved_at__month=month
    ).count()

    # ── Disputes ──────────────────────────────────────────────────────────────
    # ── Moving ────────────────────────────────────────────────────────────────
    total_companies = MovingCompanyProfile.objects.filter(is_active=True).count()
    pending_bookings = MovingBooking.objects.filter(status='pending').count()
    completed_moving = MovingBooking.objects.filter(
        status='completed', created_at__year=year, created_at__month=month
    ).count()

    return Response({
        'users': {
            'total': all_users.count(),
            'by_role': by_role,
            'new_last_30_days': new_users,
        },
        'properties': {
            'total': total_properties,
            'total_units': total_units,
            'occupied': occupied,
            'vacant': vacant,
            'occupancy_rate': occupancy_rate,
        },
        'billing': {
            'revenue_this_month': str(revenue),
            'outstanding': str(outstanding),
            'overdue_invoices': overdue_invoices,
        },
        'maintenance': {
            'submitted': maint.filter(status='submitted').count(),
            'open': maint.filter(status='open').count(),
            'assigned': maint.filter(status='assigned').count(),
            'in_progress': maint.filter(status='in_progress').count(),
            'completed_this_month': completed_this_month,
        },
        'disputes': {
            'open': Dispute.objects.filter(status='open').count(),
            'under_review': Dispute.objects.filter(status='under_review').count(),
        },
        'moving': {
            'total_companies': total_companies,
            'pending_bookings': pending_bookings,
            'completed_this_month': completed_moving,
        },
    })


# ---------------------------------------------------------------------------
# Admin — User Management
# ---------------------------------------------------------------------------

@extend_schema(
    methods=['GET'],
    summary="Admin — list all users (supports ?role=, ?search=, ?is_active=)",
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def admin_users(request):
    if not _is_admin(request.user):
        return Response({'detail': 'Admin access required.'}, status=status.HTTP_403_FORBIDDEN)

    qs = CustomUser.objects.select_related('role').all()

    role_filter = request.query_params.get('role')
    search = request.query_params.get('search')
    is_active = request.query_params.get('is_active')

    if role_filter:
        qs = qs.filter(role__name=role_filter)
    if search:
        qs = qs.filter(
            Q(username__icontains=search) |
            Q(email__icontains=search) |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search)
        )
    if is_active is not None:
        qs = qs.filter(is_active=(is_active.lower() == 'true'))

    serializer = AdminUserSerializer(qs, many=True)
    return Response(serializer.data)


@extend_schema(
    methods=['PUT'],
    summary="Admin — update user role or active status",
    examples=[
        OpenApiExample("Change role", request_only=True, value={"role": 3, "reason": "Upgraded from tenant to landlord"}),
        OpenApiExample("Deactivate", request_only=True, value={"is_active": False}),
    ],
)
@extend_schema(methods=['GET'], summary="Admin — get user detail + role change history")
@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated])
def admin_user_detail(request, pk):
    if not _is_admin(request.user):
        return Response({'detail': 'Admin access required.'}, status=status.HTTP_403_FORBIDDEN)

    try:
        user = CustomUser.objects.select_related('role').get(pk=pk)
    except CustomUser.DoesNotExist:
        return Response({'error': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        logs = RoleChangeLog.objects.filter(user=user).select_related(
            'changed_by', 'old_role', 'new_role'
        ).order_by('-changed_at')
        return Response({
            'user': AdminUserSerializer(user).data,
            'role_change_history': RoleChangeLogSerializer(logs, many=True).data,
        })

    serializer = AdminUserUpdateSerializer(user, data=request.data, partial=True)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    new_role = serializer.validated_data.get('role')
    old_role = user.role

    if new_role and new_role != old_role:
        RoleChangeLog.objects.create(
            user=user,
            changed_by=request.user,
            old_role=old_role,
            new_role=new_role,
            reason=request.data.get('reason', ''),
        )
        from notifications.utils import create_notification
        create_notification(
            user,
            'account',
            'Your Role Has Been Updated',
            f"Your account role has been changed from {old_role.name if old_role else 'none'} to {new_role.name}.",
        )

    serializer.save()
    return Response(AdminUserSerializer(user).data)


# ---------------------------------------------------------------------------
# Admin — Content Moderation (Reviews)
# ---------------------------------------------------------------------------

@extend_schema(
    methods=['GET'],
    summary="Admin — list all reviews for moderation (?type=property|tenant)",
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def admin_moderation_reviews(request):
    if not _is_admin(request.user):
        return Response({'detail': 'Admin access required.'}, status=status.HTTP_403_FORBIDDEN)

    from property.models import PropertyReview, TenantReview

    review_type = request.query_params.get('type')
    results = []

    if review_type != 'tenant':
        for r in PropertyReview.objects.select_related('reviewer', 'property').order_by('-created_at'):
            reviewer = r.reviewer
            results.append({
                'id': r.id,
                'type': 'property',
                'reviewer': reviewer.id,
                'reviewer_name': f"{reviewer.first_name} {reviewer.last_name}".strip() or reviewer.username,
                'subject_id': r.property.id,
                'subject_name': r.property.name,
                'rating': r.rating,
                'comment': r.comment,
                'created_at': r.created_at,
            })

    if review_type != 'property':
        for r in TenantReview.objects.select_related('reviewer', 'tenant', 'property').order_by('-created_at'):
            reviewer = r.reviewer
            tenant = r.tenant
            results.append({
                'id': r.id,
                'type': 'tenant',
                'reviewer': reviewer.id,
                'reviewer_name': f"{reviewer.first_name} {reviewer.last_name}".strip() or reviewer.username,
                'subject_id': tenant.id,
                'subject_name': f"{tenant.first_name} {tenant.last_name}".strip() or tenant.username,
                'rating': r.rating,
                'comment': r.comment,
                'created_at': r.created_at,
            })

    results.sort(key=lambda x: x['created_at'], reverse=True)
    return Response(results)


@extend_schema(
    methods=['DELETE'],
    summary="Admin — delete a review (?type=property|tenant required)",
)
@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def admin_moderation_review_delete(request, pk):
    if not _is_admin(request.user):
        return Response({'detail': 'Admin access required.'}, status=status.HTTP_403_FORBIDDEN)

    from property.models import PropertyReview, TenantReview

    review_type = request.query_params.get('type')
    if review_type == 'property':
        model = PropertyReview
    elif review_type == 'tenant':
        model = TenantReview
    else:
        return Response({'detail': 'Query param ?type=property|tenant is required.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        review = model.objects.get(pk=pk)
    except model.DoesNotExist:
        return Response({'error': 'Review not found.'}, status=status.HTTP_404_NOT_FOUND)

    review.delete()
    return Response({'deleted': True}, status=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Tenant Dashboard
# ---------------------------------------------------------------------------

@extend_schema(
    methods=['GET'],
    summary="Tenant dashboard — lease, invoices, maintenance, notifications",
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def tenant_dashboard(request):
    if not _is_tenant(request.user):
        return Response({'detail': 'Tenant access required.'}, status=status.HTTP_403_FORBIDDEN)

    from property.models import Lease
    from billing.models import Invoice
    from maintenance.models import MaintenanceRequest
    from notifications.models import Notification

    user = request.user
    today = date.today()

    # ── Active lease ──────────────────────────────────────────────────────────
    try:
        lease = Lease.objects.select_related('unit__property').get(tenant=user, is_active=True)
        days_remaining = (lease.end_date - today).days if lease.end_date else None
        active_lease = {
            'id': lease.id,
            'unit': lease.unit.name,
            'property': lease.unit.property.name,
            'rent_amount': str(lease.rent_amount),
            'start_date': str(lease.start_date),
            'end_date': str(lease.end_date) if lease.end_date else None,
            'days_remaining': days_remaining,
        }
    except Lease.DoesNotExist:
        active_lease = None

    # ── Invoices ──────────────────────────────────────────────────────────────
    tenant_invoices = Invoice.objects.filter(lease__tenant=user)
    next_due = tenant_invoices.filter(
        status__in=['pending', 'partial']
    ).order_by('due_date').first()

    invoices = {
        'pending': tenant_invoices.filter(status='pending').count(),
        'overdue': tenant_invoices.filter(status='overdue').count(),
        'next_due': {
            'id': next_due.id,
            'due_date': str(next_due.due_date),
            'amount': str(next_due.total_amount),
            'status': next_due.status,
        } if next_due else None,
    }

    # ── Maintenance ───────────────────────────────────────────────────────────
    open_requests = MaintenanceRequest.objects.filter(
        submitted_by=user,
        status__in=['submitted', 'open', 'assigned', 'in_progress']
    ).count()

    # ── Notifications ─────────────────────────────────────────────────────────
    unread_notifications = Notification.objects.filter(user=user, is_read=False).count()

    return Response({
        'active_lease': active_lease,
        'invoices': invoices,
        'maintenance': {'open_requests': open_requests},
        'notifications': {'unread': unread_notifications},
    })


# ---------------------------------------------------------------------------
# Artisan Dashboard
# ---------------------------------------------------------------------------

@extend_schema(
    methods=['GET'],
    summary="Artisan dashboard — open jobs, active bids, completed this month",
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def artisan_dashboard(request):
    if not _is_artisan(request.user):
        return Response({'detail': 'Artisan access required.'}, status=status.HTTP_403_FORBIDDEN)

    from maintenance.models import MaintenanceRequest, MaintenanceBid

    user = request.user
    today = date.today()
    year, month = today.year, today.month

    try:
        trade = user.artisan_profile.trade
    except Exception:
        trade = None

    # ── Open jobs matching trade ───────────────────────────────────────────────
    open_jobs_qs = MaintenanceRequest.objects.filter(status='open')
    if trade:
        open_jobs_qs = open_jobs_qs.filter(category=trade)
    open_jobs = [
        {
            'id': r.id,
            'title': r.title,
            'category': r.category,
            'priority': r.priority,
            'property': r.property_id,
            'created_at': r.created_at,
        }
        for r in open_jobs_qs.select_related('property').order_by('-created_at')[:10]
    ]

    # ── Active bids ───────────────────────────────────────────────────────────
    active_bids = MaintenanceBid.objects.filter(
        artisan=user, status__in=['pending', 'accepted']
    ).select_related('request')
    active_bids_data = [
        {
            'id': b.id,
            'request_id': b.request_id,
            'request_title': b.request.title,
            'proposed_price': str(b.proposed_price),
            'status': b.status,
            'created_at': b.created_at,
        }
        for b in active_bids
    ]

    # ── Completed this month ──────────────────────────────────────────────────
    completed_this_month = MaintenanceRequest.objects.filter(
        assigned_to=user,
        status='completed',
        resolved_at__year=year,
        resolved_at__month=month,
    ).count()

    return Response({
        'trade': trade,
        'open_jobs': {'count': len(open_jobs), 'items': open_jobs},
        'active_bids': {'count': len(active_bids_data), 'items': active_bids_data},
        'completed_this_month': completed_this_month,
    })


# ---------------------------------------------------------------------------
# Agent Dashboard
# ---------------------------------------------------------------------------

@extend_schema(
    methods=['GET'],
    summary="Agent dashboard — assigned properties, applications, maintenance, disputes",
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def agent_dashboard(request):
    if not _is_agent(request.user):
        return Response({'detail': 'Agent access required.'}, status=status.HTTP_403_FORBIDDEN)

    from property.models import Property, PropertyAgent, TenantApplication, Unit
    from maintenance.models import MaintenanceRequest
    from disputes.models import Dispute

    user = request.user

    assigned = PropertyAgent.objects.filter(agent=user).select_related('property')
    prop_ids = [pa.property_id for pa in assigned]
    properties = Property.objects.filter(id__in=prop_ids).prefetch_related('units')

    total_units = sum(p.units.count() for p in properties)
    occupied = sum(p.units.filter(is_occupied=True).count() for p in properties)
    occupancy_rate = f"{(occupied / total_units * 100):.1f}%" if total_units else "0%"

    assigned_properties = [
        {
            'id': p.id,
            'name': p.name,
            'property_type': p.property_type,
            'total_units': p.units.count(),
            'occupied_units': p.units.filter(is_occupied=True).count(),
        }
        for p in properties
    ]

    pending_applications = TenantApplication.objects.filter(
        unit__property__in=prop_ids, status='pending'
    ).count()

    open_maintenance = MaintenanceRequest.objects.filter(
        property__in=prop_ids,
        status__in=['submitted', 'open', 'assigned', 'in_progress']
    ).count()

    active_disputes = Dispute.objects.filter(
        property__in=prop_ids,
        status__in=['open', 'under_review']
    ).count()

    return Response({
        'assigned_properties': {
            'count': len(assigned_properties),
            'total_units': total_units,
            'occupied_units': occupied,
            'occupancy_rate': occupancy_rate,
            'items': assigned_properties,
        },
        'pending_applications': pending_applications,
        'open_maintenance_requests': open_maintenance,
        'active_disputes': active_disputes,
    })


# ---------------------------------------------------------------------------
# Moving Company Dashboard
# ---------------------------------------------------------------------------

@extend_schema(
    methods=['GET'],
    summary="Moving company dashboard — bookings summary, reviews",
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def moving_company_dashboard(request):
    if not _is_moving_company(request.user):
        return Response({'detail': 'Moving company access required.'}, status=status.HTTP_403_FORBIDDEN)

    from moving.models import MovingBooking, MovingCompanyReview
    from authentication.models import MovingCompanyProfile

    user = request.user
    today = date.today()
    year, month = today.year, today.month

    try:
        profile = user.moving_company_profile
    except MovingCompanyProfile.DoesNotExist:
        return Response({'detail': 'No company profile found. Please create one via /api/auth/me/profile/.'}, status=status.HTTP_404_NOT_FOUND)

    bookings = MovingBooking.objects.filter(company=profile)
    completed_this_month = bookings.filter(
        status='completed', created_at__year=year, created_at__month=month
    ).count()

    recent_reviews = MovingCompanyReview.objects.filter(
        company=profile
    ).select_related('reviewer').order_by('-created_at')[:5]

    all_ratings = list(MovingCompanyReview.objects.filter(company=profile).values_list('rating', flat=True))
    avg_rating = round(sum(all_ratings) / len(all_ratings), 2) if all_ratings else None

    reviews_data = [
        {
            'id': r.id,
            'reviewer_name': f"{r.reviewer.first_name} {r.reviewer.last_name}".strip() or r.reviewer.username,
            'rating': r.rating,
            'comment': r.comment,
            'created_at': r.created_at,
        }
        for r in recent_reviews
    ]

    return Response({
        'company_name': profile.company_name,
        'is_verified': profile.is_verified,
        'bookings': {
            'pending': bookings.filter(status='pending').count(),
            'confirmed': bookings.filter(status='confirmed').count(),
            'in_progress': bookings.filter(status='in_progress').count(),
            'completed_this_month': completed_this_month,
            'cancelled': bookings.filter(status='cancelled').count(),
            'total': bookings.count(),
        },
        'reviews': {
            'total': len(all_ratings),
            'average_rating': avg_rating,
            'recent': reviews_data,
        },
    })
