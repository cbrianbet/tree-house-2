from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema, OpenApiExample
from .models import Property, Unit, PropertyImage, Lease, PropertyAgent
from .serializers import PropertySerializer, UnitSerializer, PropertyImageSerializer, LeaseSerializer, PropertyAgentSerializer


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
        serializer = UnitSerializer(unit, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save(updated_by=request.user)
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


@extend_schema(methods=['GET'], summary="List publicly available units (no auth required)")
@api_view(['GET'])
@permission_classes([AllowAny])
def public_units(request):
    units = Unit.objects.filter(is_occupied=False, is_public=True)
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
