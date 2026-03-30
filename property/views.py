import math
from datetime import date, timedelta
from decimal import Decimal
from django.db import IntegrityError

from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema, OpenApiExample
from .models import Property, Unit, PropertyImage, Lease, PropertyAgent, TenantApplication, LeaseDocument, PropertyReview, TenantReview, SavedSearch
from .serializers import (
    PropertySerializer, UnitSerializer, PropertyImageSerializer,
    LeaseSerializer, PropertyAgentSerializer, TenantApplicationSerializer,
    LeaseDocumentSerializer, PropertyReviewSerializer, TenantReviewSerializer,
    SavedSearchSerializer,
)


def is_landlord(user):
    return user.is_authenticated and hasattr(user, 'role') and user.role.name == 'Landlord'


def is_admin(user):
    return user.is_staff or (hasattr(user, 'role') and user.role.name == 'Admin')


def is_agent_for(user, property):
    return (
        user.is_authenticated
        and hasattr(user, 'role')
        and user.role.name == 'Agent'
        and PropertyAgent.objects.filter(agent=user, property=property).exists()
    )


def is_tenant(user):
    from authentication.models import Role
    return user.is_authenticated and hasattr(user, 'role') and user.role.name == Role.TENANT


@extend_schema(methods=['GET'], summary="List properties")
@extend_schema(
    methods=['POST'],
    summary="Create a property",
    examples=[
        OpenApiExample("Create property", request_only=True, value={
            "name": "Sunset Apartments",
            "description": "Modern apartments in Westlands",
            "property_type": "apartment",
            "longitude": 36.8129,
            "latitude": -1.2641,
        })
    ],
)
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def property_list_create(request):
    if request.method == 'GET':
        if is_admin(request.user):
            properties = Property.objects.all()
        elif is_landlord(request.user):
            properties = Property.objects.filter(owner=request.user)
        else:
            # Agents see properties they're assigned to
            assigned_ids = PropertyAgent.objects.filter(agent=request.user).values_list('property_id', flat=True)
            properties = Property.objects.filter(id__in=assigned_ids)
        serializer = PropertySerializer(properties, many=True)
        return Response(serializer.data)

    elif request.method == 'POST':
        if not is_landlord(request.user):
            return Response({'detail': 'Only landlords can add properties.'}, status=status.HTTP_403_FORBIDDEN)
        serializer = PropertySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(owner=request.user, created_by=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(methods=['GET'], summary="Get a property")
@extend_schema(
    methods=['PUT'],
    summary="Update a property",
    examples=[
        OpenApiExample("Update property", request_only=True, value={
            "name": "Sunset Apartments Phase 2",
            "description": "Updated description",
        })
    ],
)
@extend_schema(methods=['DELETE'], summary="Delete a property")
@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def property_detail(request, pk):
    try:
        property = Property.objects.get(pk=pk)
    except Property.DoesNotExist:
        return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

    if not (is_admin(request.user) or property.owner == request.user or is_agent_for(request.user, property)):
        return Response({'detail': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)

    if request.method == 'GET':
        serializer = PropertySerializer(property)
        return Response(serializer.data)

    elif request.method == 'PUT':
        serializer = PropertySerializer(property, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save(updated_by=request.user)
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'DELETE':
        if not (is_admin(request.user) or property.owner == request.user):
            return Response({'detail': 'Only the owner or admin can delete a property.'}, status=status.HTTP_403_FORBIDDEN)
        property.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(methods=['GET'], summary="List units for a property")
@extend_schema(
    methods=['POST'],
    summary="Add a unit to a property",
    examples=[
        OpenApiExample("Create unit", request_only=True, value={
            "name": "Unit A1",
            "floor": "1st",
            "description": "Spacious 2 bedroom unit",
            "bedrooms": 2,
            "bathrooms": 1,
            "parking_space": True,
            "parking_slots": 1,
            "price": "45000.00",
            "service_charge": "3000.00",
            "security_deposit": "90000.00",
            "is_public": True,
        })
    ],
)
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def unit_list_create(request, property_id):
    try:
        property = Property.objects.get(pk=property_id)
    except Property.DoesNotExist:
        return Response({'detail': 'Property not found.'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        units = property.units.all()
        serializer = UnitSerializer(units, many=True)
        return Response(serializer.data)

    elif request.method == 'POST':
        if not (is_admin(request.user) or property.owner == request.user or is_agent_for(request.user, property)):
            return Response({'detail': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)
        serializer = UnitSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(property=property, created_by=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(methods=['GET'], summary="Get a unit")
@extend_schema(
    methods=['PUT'],
    summary="Update a unit",
    examples=[
        OpenApiExample("Update unit", request_only=True, value={
            "price": "50000.00",
            "is_public": False,
        })
    ],
)
@extend_schema(methods=['DELETE'], summary="Delete a unit")
@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def unit_detail(request, pk):
    try:
        unit = Unit.objects.get(pk=pk)
    except Unit.DoesNotExist:
        return Response({'detail': 'Unit not found.'}, status=status.HTTP_404_NOT_FOUND)

    if not (is_admin(request.user) or unit.property.owner == request.user or is_agent_for(request.user, unit.property)):
        return Response({'detail': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)

    if request.method == 'GET':
        serializer = UnitSerializer(unit)
        return Response(serializer.data)

    elif request.method == 'PUT':
        was_public = unit.is_public
        serializer = UnitSerializer(unit, data=request.data, partial=True)
        if serializer.is_valid():
            updated_unit = serializer.save(updated_by=request.user)
            if not was_public and updated_unit.is_public:
                from .utils import notify_saved_search_matches
                notify_saved_search_matches(updated_unit)
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'DELETE':
        if not (is_admin(request.user) or unit.property.owner == request.user):
            return Response({'detail': 'Only the owner or admin can delete a unit.'}, status=status.HTTP_403_FORBIDDEN)
        unit.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(methods=['GET'], summary="List images for a unit")
@extend_schema(methods=['POST'], summary="Upload an image for a unit")
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def unit_image_list_create(request, unit_id):
    try:
        unit = Unit.objects.get(pk=unit_id)
    except Unit.DoesNotExist:
        return Response({'detail': 'Unit not found.'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        images = PropertyImage.objects.filter(property=unit.property)
        serializer = PropertyImageSerializer(images, many=True)
        return Response(serializer.data)

    elif request.method == 'POST':
        if not (is_admin(request.user) or unit.property.owner == request.user or is_agent_for(request.user, unit.property)):
            return Response({'detail': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)
        serializer = PropertyImageSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(property=unit.property)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(methods=['GET'], summary="Get lease for a unit")
@extend_schema(
    methods=['POST'],
    summary="Create a lease for a unit",
    examples=[
        OpenApiExample("Create lease", request_only=True, value={
            "tenant": 5,
            "start_date": "2026-04-01",
            "end_date": "2027-03-31",
            "rent_amount": "45000.00",
        })
    ],
)
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def lease_list_create(request, unit_id):
    try:
        unit = Unit.objects.get(pk=unit_id)
    except Unit.DoesNotExist:
        return Response({'detail': 'Unit not found.'}, status=status.HTTP_404_NOT_FOUND)

    if not (is_admin(request.user) or unit.property.owner == request.user or is_agent_for(request.user, unit.property)):
        return Response({'detail': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)

    if request.method == 'GET':
        lease = getattr(unit, 'lease', None)
        if lease:
            serializer = LeaseSerializer(lease)
            return Response(serializer.data)
        return Response({'detail': 'No lease for this unit.'}, status=status.HTTP_404_NOT_FOUND)

    elif request.method == 'POST':
        serializer = LeaseSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(unit=unit)
            unit.is_occupied = True
            unit.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    methods=['GET'],
    summary="Browse publicly available units (no auth required)",
    examples=[
        OpenApiExample("Filter by price and bedrooms", request_only=True, value={
            "price_min": 10000,
            "price_max": 50000,
            "bedrooms": 2,
            "property_type": "apartment",
        }),
    ],
)
@api_view(['GET'])
@permission_classes([AllowAny])
def public_units(request):
    units = Unit.objects.filter(is_occupied=False, is_public=True).select_related('property')

    # Price filters
    price_min = request.GET.get('price_min')
    price_max = request.GET.get('price_max')
    if price_min:
        try:
            units = units.filter(price__gte=float(price_min))
        except ValueError:
            pass
    if price_max:
        try:
            units = units.filter(price__lte=float(price_max))
        except ValueError:
            pass

    # Bedroom / bathroom filters (at least N)
    bedrooms = request.GET.get('bedrooms')
    bathrooms = request.GET.get('bathrooms')
    if bedrooms:
        try:
            units = units.filter(bedrooms__gte=int(bedrooms))
        except ValueError:
            pass
    if bathrooms:
        try:
            units = units.filter(bathrooms__gte=int(bathrooms))
        except ValueError:
            pass

    # Property type
    property_type = request.GET.get('property_type')
    if property_type:
        units = units.filter(property__property_type=property_type)

    # Amenities keyword
    amenities = request.GET.get('amenities')
    if amenities:
        units = units.filter(amenities__icontains=amenities)

    # Parking
    parking = request.GET.get('parking')
    if parking and parking.lower() == 'true':
        units = units.filter(parking_space=True)

    # Location: lat/lng/radius_km bounding box
    lat_param = request.GET.get('lat')
    lng_param = request.GET.get('lng')
    radius_param = request.GET.get('radius_km')
    if lat_param and lng_param and radius_param:
        try:
            lat = float(lat_param)
            lng = float(lng_param)
            radius_km = float(radius_param)
            lat_delta = radius_km / 111.0
            lng_delta = radius_km / (111.0 * abs(math.cos(math.radians(lat))) or 1)
            units = units.filter(
                property__latitude__gte=lat - lat_delta,
                property__latitude__lte=lat + lat_delta,
                property__longitude__gte=lng - lng_delta,
                property__longitude__lte=lng + lng_delta,
            )
        except ValueError:
            pass

    serializer = UnitSerializer(units, many=True)
    return Response(serializer.data)


@extend_schema(methods=['GET'], summary="List agents assigned to a property")
@extend_schema(
    methods=['POST'],
    summary="Appoint an agent to manage a property",
    examples=[
        OpenApiExample("Appoint agent", request_only=True, value={"agent": 3})
    ],
)
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def property_agent_list_create(request, property_id):
    try:
        property = Property.objects.get(pk=property_id)
    except Property.DoesNotExist:
        return Response({'detail': 'Property not found.'}, status=status.HTTP_404_NOT_FOUND)

    if not (is_admin(request.user) or property.owner == request.user):
        return Response({'detail': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)

    if request.method == 'GET':
        agents = PropertyAgent.objects.filter(property=property).select_related('agent', 'appointed_by')
        serializer = PropertyAgentSerializer(agents, many=True)
        return Response(serializer.data)

    elif request.method == 'POST':
        if not (is_landlord(request.user) and property.owner == request.user):
            return Response({'detail': 'Only the property owner can appoint agents.'}, status=status.HTTP_403_FORBIDDEN)
        agent_id = request.data.get('agent')
        try:
            agent_user = __import__('authentication.models', fromlist=['CustomUser']).CustomUser.objects.get(pk=agent_id, role__name='Agent')
        except Exception:
            return Response({'detail': 'Agent user not found.'}, status=status.HTTP_400_BAD_REQUEST)
        pa, created = PropertyAgent.objects.get_or_create(
            property=property, agent=agent_user,
            defaults={'appointed_by': request.user}
        )
        if not created:
            return Response({'detail': 'Agent already assigned to this property.'}, status=status.HTTP_400_BAD_REQUEST)
        serializer = PropertyAgentSerializer(pa)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


@extend_schema(methods=['DELETE'], summary="Remove an agent from a property")
@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def property_agent_detail(request, property_id, agent_id):
    try:
        property = Property.objects.get(pk=property_id)
    except Property.DoesNotExist:
        return Response({'detail': 'Property not found.'}, status=status.HTTP_404_NOT_FOUND)

    if not (is_admin(request.user) or property.owner == request.user):
        return Response({'detail': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)

    try:
        pa = PropertyAgent.objects.get(property=property, agent_id=agent_id)
    except PropertyAgent.DoesNotExist:
        return Response({'detail': 'Agent not assigned to this property.'}, status=status.HTTP_404_NOT_FOUND)

    pa.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


# ── Tenant Applications ──────────────────────────────────────────────────────

@extend_schema(methods=['GET'], summary="List tenant applications")
@extend_schema(
    methods=['POST'],
    summary="Submit a tenant application for a unit",
    examples=[
        OpenApiExample("Apply for unit", request_only=True, value={
            "unit": 2,
            "message": "I am a working professional looking for a quiet 2-bed unit.",
        }),
    ],
)
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def application_list_create(request):
    user = request.user

    if request.method == 'GET':
        if is_admin(user):
            qs = TenantApplication.objects.select_related('unit__property', 'applicant').all()
        elif is_landlord(user):
            qs = TenantApplication.objects.filter(unit__property__owner=user).select_related('unit__property', 'applicant')
        else:
            qs = TenantApplication.objects.filter(applicant=user).select_related('unit__property')
        return Response(TenantApplicationSerializer(qs, many=True).data)

    elif request.method == 'POST':
        if not (hasattr(user, 'role') and user.role.name == 'Tenant'):
            return Response({'detail': 'Only tenants can submit applications.'}, status=status.HTTP_403_FORBIDDEN)

        serializer = TenantApplicationSerializer(data=request.data)
        if serializer.is_valid():
            unit = serializer.validated_data['unit']
            if unit.is_occupied:
                return Response({'detail': 'This unit is already occupied.'}, status=status.HTTP_400_BAD_REQUEST)
            try:
                serializer.save(applicant=user)
            except IntegrityError:
                return Response({'detail': 'You have already applied for this unit.'}, status=status.HTTP_400_BAD_REQUEST)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(methods=['GET'], summary="Get application detail")
@extend_schema(
    methods=['PUT'],
    summary="Update application status",
    examples=[
        OpenApiExample("Approve (landlord)", request_only=True, value={
            "status": "approved",
            "start_date": "2024-04-01",
            "end_date": "2025-03-31",
            "rent_amount": "25000.00",
        }),
        OpenApiExample("Reject (landlord)", request_only=True, value={"status": "rejected"}),
        OpenApiExample("Withdraw (tenant)", request_only=True, value={"status": "withdrawn"}),
    ],
)
@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated])
def application_detail(request, pk):
    try:
        app = TenantApplication.objects.select_related('unit__property', 'applicant').get(pk=pk)
    except TenantApplication.DoesNotExist:
        return Response({'detail': 'Application not found.'}, status=status.HTTP_404_NOT_FOUND)

    user = request.user
    is_owner = app.unit.property.owner == user
    is_applicant = app.applicant == user

    if not (is_admin(user) or is_owner or is_applicant):
        return Response({'detail': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)

    if request.method == 'GET':
        return Response(TenantApplicationSerializer(app).data)

    new_status = request.data.get('status')

    if new_status == 'withdrawn':
        if not is_applicant:
            return Response({'detail': 'Only the applicant can withdraw.'}, status=status.HTTP_403_FORBIDDEN)
        if app.status != 'pending':
            return Response({'detail': 'Only pending applications can be withdrawn.'}, status=status.HTTP_400_BAD_REQUEST)
        app.status = 'withdrawn'
        app.save()
        return Response(TenantApplicationSerializer(app).data)

    if new_status in ('approved', 'rejected'):
        if not (is_admin(user) or is_owner):
            return Response({'detail': 'Only the property owner can approve or reject applications.'}, status=status.HTTP_403_FORBIDDEN)
        if app.status != 'pending':
            return Response({'detail': 'Only pending applications can be reviewed.'}, status=status.HTTP_400_BAD_REQUEST)

        if new_status == 'approved':
            if app.unit.is_occupied:
                return Response({'detail': 'Unit is already occupied.'}, status=status.HTTP_400_BAD_REQUEST)
            start_date = request.data.get('start_date')
            rent_amount = request.data.get('rent_amount')
            end_date = request.data.get('end_date')
            if not start_date or not rent_amount:
                return Response({'detail': 'start_date and rent_amount are required to approve.'}, status=status.HTTP_400_BAD_REQUEST)
            Lease.objects.create(
                unit=app.unit,
                tenant=app.applicant,
                start_date=start_date,
                end_date=end_date,
                rent_amount=rent_amount,
            )
            app.unit.is_occupied = True
            app.unit.save()
            # Reject all other pending applications for the same unit
            TenantApplication.objects.filter(unit=app.unit, status='pending').exclude(pk=pk).update(status='rejected')

        app.status = new_status
        app.reviewed_by = user
        app.reviewed_at = timezone.now()
        app.save()
        return Response(TenantApplicationSerializer(app).data)

    return Response({'detail': 'Invalid status.'}, status=status.HTTP_400_BAD_REQUEST)


# ── Landlord Dashboard ───────────────────────────────────────────────────────

@extend_schema(
    methods=['GET'],
    summary="Landlord dashboard — portfolio overview",
    examples=[
        OpenApiExample("Dashboard response", value={
            "properties": {"total": 3, "total_units": 24, "occupied_units": 19, "vacant_units": 5, "occupancy_rate": "79.2%"},
            "adverts": {"count": 5, "units": [{"id": 2, "name": "A1", "property": "Sunset Apartments", "price": "25000.00"}]},
            "applications": {"pending": 4, "approved_this_month": 2},
            "leases_ending_soon": [{"id": 1, "unit": "A1", "property": "Sunset Apartments", "tenant": "jane", "end_date": "2024-04-30", "days_remaining": 32}],
            "billing": {"overdue_invoices": 3, "collected_this_month": "135000.00", "outstanding": "45000.00"},
            "maintenance": {"submitted": 2, "open": 1, "in_progress": 3},
            "performance": {"period": "2024-03", "by_property": [{"id": 1, "name": "Sunset Apartments", "net_income": "117500.00", "occupancy_rate": "83.3%"}]},
        }),
    ],
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def landlord_dashboard(request):
    user = request.user
    if not (is_admin(user) or is_landlord(user)):
        return Response({'detail': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)

    from billing.models import Payment, Invoice, Expense, AdditionalIncome
    from maintenance.models import MaintenanceRequest
    from django.db.models import Sum, Count

    today = date.today()
    year, month = today.year, today.month
    lease_warning_date = today + timedelta(days=60)

    # ── Properties & units ───────────────────────────────────────────────────
    if is_admin(user):
        properties = Property.objects.prefetch_related('units').all()
    else:
        properties = Property.objects.filter(owner=user).prefetch_related('units')

    prop_ids = [p.id for p in properties]
    total_units = sum(p.units.count() for p in properties)
    occupied_units = sum(p.units.filter(is_occupied=True).count() for p in properties)
    vacant_units = total_units - occupied_units
    occupancy_rate = f"{(occupied_units / total_units * 100):.1f}%" if total_units else "0%"

    # ── Current adverts (public + vacant) ───────────────────────────────────
    advert_qs = Unit.objects.filter(
        property__in=properties, is_public=True, is_occupied=False
    ).select_related('property')
    adverts = [
        {'id': u.id, 'name': u.name, 'property': u.property.name, 'price': str(u.price or 0)}
        for u in advert_qs
    ]

    # ── Applications ─────────────────────────────────────────────────────────
    app_base = TenantApplication.objects.filter(unit__property__in=properties)
    pending_apps = app_base.filter(status='pending').count()
    approved_this_month = app_base.filter(
        status='approved', reviewed_at__year=year, reviewed_at__month=month
    ).count()

    # ── Leases ending within 60 days ─────────────────────────────────────────
    ending_leases = Lease.objects.filter(
        unit__property__in=properties,
        is_active=True,
        end_date__isnull=False,
        end_date__lte=lease_warning_date,
        end_date__gte=today,
    ).select_related('unit__property', 'tenant')
    leases_ending = [
        {
            'id': l.id,
            'unit': l.unit.name,
            'property': l.unit.property.name,
            'tenant': l.tenant.username,
            'end_date': str(l.end_date),
            'days_remaining': (l.end_date - today).days,
        }
        for l in ending_leases
    ]

    # ── Billing (current month) ───────────────────────────────────────────────
    collected = Payment.objects.filter(
        status='completed',
        invoice__lease__unit__property__in=properties,
        paid_at__year=year, paid_at__month=month,
    ).aggregate(t=Sum('amount'))['t'] or Decimal('0')

    overdue_count = Invoice.objects.filter(
        lease__unit__property__in=properties, status='overdue'
    ).count()

    outstanding = Invoice.objects.filter(
        lease__unit__property__in=properties,
        status__in=['pending', 'partial', 'overdue'],
    ).aggregate(t=Sum('total_amount'))['t'] or Decimal('0')

    # ── Maintenance ───────────────────────────────────────────────────────────
    maint_base = MaintenanceRequest.objects.filter(property__in=properties)
    maintenance = {
        s: maint_base.filter(status=s).count()
        for s in ('submitted', 'open', 'in_progress', 'assigned')
    }

    # ── Per-property performance (current month) ──────────────────────────────
    perf = []
    for prop in properties:
        p_collected = Payment.objects.filter(
            status='completed',
            invoice__lease__unit__property=prop,
            paid_at__year=year, paid_at__month=month,
        ).aggregate(t=Sum('amount'))['t'] or Decimal('0')

        p_ai = AdditionalIncome.objects.filter(
            unit__property=prop, date__year=year, date__month=month,
        ).aggregate(t=Sum('amount'))['t'] or Decimal('0')

        p_exp = Expense.objects.filter(
            property=prop, date__year=year, date__month=month,
        ).aggregate(t=Sum('amount'))['t'] or Decimal('0')

        p_units = prop.units.count()
        p_occupied = prop.units.filter(is_occupied=True).count()
        net = p_collected + p_ai - p_exp

        perf.append({
            'id': prop.id,
            'name': prop.name,
            'net_income': str(net),
            'total_units': p_units,
            'occupied_units': p_occupied,
            'occupancy_rate': f"{(p_occupied / p_units * 100):.1f}%" if p_units else "0%",
        })

    perf.sort(key=lambda x: Decimal(x['net_income']), reverse=True)

    return Response({
        'properties': {
            'total': len(properties),
            'total_units': total_units,
            'occupied_units': occupied_units,
            'vacant_units': vacant_units,
            'occupancy_rate': occupancy_rate,
        },
        'adverts': {
            'count': len(adverts),
            'units': adverts,
        },
        'applications': {
            'pending': pending_apps,
            'approved_this_month': approved_this_month,
        },
        'leases_ending_soon': leases_ending,
        'billing': {
            'overdue_invoices': overdue_count,
            'collected_this_month': str(collected),
            'outstanding': str(outstanding),
        },
        'maintenance': maintenance,
        'performance': {
            'period': f"{year}-{month:02d}",
            'by_property': perf,
        },
    })


# ── Lease Documents ───────────────────────────────────────────────────────────

@extend_schema(methods=['GET'], summary="List documents for a lease")
@extend_schema(
    methods=['POST'],
    summary="Upload a document for a lease",
    examples=[
        OpenApiExample("Upload lease document", request_only=True, value={
            "document_type": "lease_agreement",
            "title": "Signed Lease Agreement 2026",
            "file_url": "https://storage.example.com/leases/doc-001.pdf",
        })
    ],
)
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def lease_document_list_create(request, lease_id):
    try:
        lease = Lease.objects.select_related('unit__property', 'tenant').get(pk=lease_id)
    except Lease.DoesNotExist:
        return Response({'detail': 'Lease not found.'}, status=status.HTTP_404_NOT_FOUND)

    prop = lease.unit.property
    is_owner = prop.owner == request.user
    is_assigned_agent = is_agent_for(request.user, prop)
    is_lease_tenant = lease.tenant == request.user

    if not (is_admin(request.user) or is_owner or is_assigned_agent or is_lease_tenant):
        return Response({'detail': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)

    if request.method == 'GET':
        docs = LeaseDocument.objects.filter(lease=lease).select_related('uploaded_by', 'signed_by')
        serializer = LeaseDocumentSerializer(docs, many=True)
        return Response(serializer.data)

    elif request.method == 'POST':
        if not (is_admin(request.user) or is_owner or is_assigned_agent):
            return Response({'detail': 'Only the landlord or assigned agent can upload documents.'}, status=status.HTTP_403_FORBIDDEN)
        serializer = LeaseDocumentSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(lease=lease, uploaded_by=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    methods=['POST'],
    summary="Sign a lease document (tenant only)",
    examples=[
        OpenApiExample("Sign document", request_only=True, value={}),
    ],
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def lease_document_sign(request, lease_id, doc_id):
    try:
        lease = Lease.objects.select_related('unit__property', 'tenant').get(pk=lease_id)
    except Lease.DoesNotExist:
        return Response({'detail': 'Lease not found.'}, status=status.HTTP_404_NOT_FOUND)

    if lease.tenant != request.user:
        return Response({'detail': 'Only the tenant on this lease can sign documents.'}, status=status.HTTP_403_FORBIDDEN)

    try:
        doc = LeaseDocument.objects.get(pk=doc_id, lease=lease)
    except LeaseDocument.DoesNotExist:
        return Response({'detail': 'Document not found.'}, status=status.HTTP_404_NOT_FOUND)

    if doc.signed_by is not None:
        return Response({'detail': 'Document has already been signed.'}, status=status.HTTP_400_BAD_REQUEST)

    doc.signed_by = request.user
    doc.signed_at = timezone.now()
    doc.save()
    return Response(LeaseDocumentSerializer(doc).data)


# ── Property Reviews ──────────────────────────────────────────────────────────

@extend_schema(methods=['GET'], summary="List reviews for a property")
@extend_schema(
    methods=['POST'],
    summary="Submit a review for a property (tenants with a lease only)",
    examples=[
        OpenApiExample("Submit property review", request_only=True, value={
            "rating": 4,
            "comment": "Great location and well-maintained property.",
        })
    ],
)
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def property_review_list_create(request, property_id):
    try:
        prop = Property.objects.get(pk=property_id)
    except Property.DoesNotExist:
        return Response({'detail': 'Property not found.'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        reviews = PropertyReview.objects.filter(property=prop).select_related('reviewer')
        serializer = PropertyReviewSerializer(reviews, many=True)
        return Response(serializer.data)

    elif request.method == 'POST':
        user = request.user
        is_owner = prop.owner == user
        if not is_owner:
            if is_tenant(user):
                has_lease = Lease.objects.filter(unit__property=prop, tenant=user).exists()
                if not has_lease:
                    return Response({'detail': 'You must have or have had a lease on this property to review it.'}, status=status.HTTP_403_FORBIDDEN)
            else:
                return Response({'detail': 'Only tenants with a lease or the property owner can review this property.'}, status=status.HTTP_403_FORBIDDEN)

        serializer = PropertyReviewSerializer(data=request.data)
        if serializer.is_valid():
            try:
                serializer.save(reviewer=user, property=prop)
            except IntegrityError:
                return Response({'detail': 'You have already reviewed this property.'}, status=status.HTTP_400_BAD_REQUEST)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(methods=['GET'], summary="Get a property review")
@extend_schema(
    methods=['PATCH'],
    summary="Update own property review",
    examples=[
        OpenApiExample("Update review", request_only=True, value={"rating": 5, "comment": "Updated: excellent property."})
    ],
)
@extend_schema(methods=['DELETE'], summary="Delete own property review")
@api_view(['GET', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def property_review_detail(request, property_id, review_id):
    try:
        prop = Property.objects.get(pk=property_id)
    except Property.DoesNotExist:
        return Response({'detail': 'Property not found.'}, status=status.HTTP_404_NOT_FOUND)

    try:
        review = PropertyReview.objects.select_related('reviewer').get(pk=review_id, property=prop)
    except PropertyReview.DoesNotExist:
        return Response({'detail': 'Review not found.'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        return Response(PropertyReviewSerializer(review).data)

    if review.reviewer != request.user:
        return Response({'detail': 'You can only modify your own review.'}, status=status.HTTP_403_FORBIDDEN)

    if request.method == 'PATCH':
        serializer = PropertyReviewSerializer(review, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'DELETE':
        review.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ── Tenant Reviews ────────────────────────────────────────────────────────────

@extend_schema(methods=['GET'], summary="List tenant reviews for a property")
@extend_schema(
    methods=['POST'],
    summary="Submit a review for a tenant (landlord only)",
    examples=[
        OpenApiExample("Submit tenant review", request_only=True, value={
            "tenant": 5,
            "rating": 5,
            "comment": "Excellent tenant. Always paid on time and kept the unit clean.",
        })
    ],
)
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def tenant_review_list_create(request, property_id):
    try:
        prop = Property.objects.get(pk=property_id)
    except Property.DoesNotExist:
        return Response({'detail': 'Property not found.'}, status=status.HTTP_404_NOT_FOUND)

    is_owner = prop.owner == request.user
    is_assigned_agent = is_agent_for(request.user, prop)

    if not (is_admin(request.user) or is_owner or is_assigned_agent):
        return Response({'detail': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)

    if request.method == 'GET':
        reviews = TenantReview.objects.filter(property=prop).select_related('reviewer', 'tenant')
        serializer = TenantReviewSerializer(reviews, many=True)
        return Response(serializer.data)

    elif request.method == 'POST':
        if not (is_landlord(request.user) and is_owner):
            return Response({'detail': 'Only the property owner can review tenants.'}, status=status.HTTP_403_FORBIDDEN)

        tenant_id = request.data.get('tenant')
        from authentication.models import CustomUser as AuthUser
        try:
            reviewed_tenant = AuthUser.objects.get(pk=tenant_id, role__name='Tenant')
        except AuthUser.DoesNotExist:
            return Response({'detail': 'Tenant user not found.'}, status=status.HTTP_400_BAD_REQUEST)

        has_lease = Lease.objects.filter(unit__property=prop, tenant=reviewed_tenant).exists()
        if not has_lease:
            return Response({'detail': 'This tenant has not had a lease on this property.'}, status=status.HTTP_403_FORBIDDEN)

        serializer = TenantReviewSerializer(data=request.data)
        if serializer.is_valid():
            try:
                serializer.save(reviewer=request.user, tenant=reviewed_tenant, property=prop)
            except IntegrityError:
                return Response({'detail': 'You have already reviewed this tenant for this property.'}, status=status.HTTP_400_BAD_REQUEST)
            # TODO: trigger notification after merge
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(methods=['GET'], summary="Get a tenant review")
@extend_schema(
    methods=['PATCH'],
    summary="Update own tenant review",
    examples=[
        OpenApiExample("Update tenant review", request_only=True, value={"rating": 4, "comment": "Good tenant overall."})
    ],
)
@extend_schema(methods=['DELETE'], summary="Delete own tenant review")
@api_view(['GET', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def tenant_review_detail(request, property_id, review_id):
    try:
        prop = Property.objects.get(pk=property_id)
    except Property.DoesNotExist:
        return Response({'detail': 'Property not found.'}, status=status.HTTP_404_NOT_FOUND)

    try:
        review = TenantReview.objects.select_related('reviewer', 'tenant').get(pk=review_id, property=prop)
    except TenantReview.DoesNotExist:
        return Response({'detail': 'Review not found.'}, status=status.HTTP_404_NOT_FOUND)

    is_owner = prop.owner == request.user
    is_assigned_agent = is_agent_for(request.user, prop)

    if request.method == 'GET':
        if not (is_admin(request.user) or is_owner or is_assigned_agent):
            return Response({'detail': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)
        return Response(TenantReviewSerializer(review).data)

    if review.reviewer != request.user:
        return Response({'detail': 'You can only modify your own review.'}, status=status.HTTP_403_FORBIDDEN)

    if request.method == 'PATCH':
        serializer = TenantReviewSerializer(review, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'DELETE':
        review.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ── Saved Searches ────────────────────────────────────────────────────────────

@extend_schema(methods=['GET'], summary="List own saved searches")
@extend_schema(
    methods=['POST'],
    summary="Create a saved search",
    examples=[
        OpenApiExample("Apartment in Westlands", request_only=True, value={
            "name": "2-bed apartments under 50k",
            "filters": {
                "price_max": 50000,
                "bedrooms": 2,
                "property_type": "apartment",
                "lat": -1.2921,
                "lng": 36.8172,
                "radius_km": 5,
            },
            "notify_on_match": True,
        }),
    ],
)
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def saved_search_list_create(request):
    user = request.user

    if request.method == 'GET':
        if is_admin(user):
            searches = SavedSearch.objects.all()
        else:
            searches = SavedSearch.objects.filter(user=user)
        return Response(SavedSearchSerializer(searches, many=True).data)

    serializer = SavedSearchSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(user=user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(methods=['GET'], summary="Get a saved search")
@extend_schema(methods=['PATCH'], summary="Update a saved search", examples=[
    OpenApiExample("Update filters", request_only=True, value={"filters": {"price_max": 60000}}),
])
@extend_schema(methods=['DELETE'], summary="Delete a saved search")
@api_view(['GET', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def saved_search_detail(request, pk):
    try:
        search = SavedSearch.objects.get(pk=pk)
    except SavedSearch.DoesNotExist:
        return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

    if search.user != request.user and not is_admin(request.user):
        return Response({'detail': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)

    if request.method == 'GET':
        return Response(SavedSearchSerializer(search).data)

    if request.method == 'PATCH':
        serializer = SavedSearchSerializer(search, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    search.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)
