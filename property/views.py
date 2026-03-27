from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from .models import Property, Unit, PropertyImage, Lease
from .serializers import PropertySerializer, UnitSerializer, PropertyImageSerializer, LeaseSerializer
from authentication.models import CustomUser, Role


def is_landlord(user):
    return user.is_authenticated and hasattr(user, 'role') and user.role.name == 'landlord'


def is_admin(user):
    return user.is_staff or (hasattr(user, 'role') and user.role.name == 'admin')


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def property_list_create(request):
    if request.method == 'GET':
        if is_admin(request.user):
            properties = Property.objects.all()
        else:
            properties = Property.objects.filter(owner=request.user)
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


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def property_detail(request, pk):
    try:
        property = Property.objects.get(pk=pk)
    except Property.DoesNotExist:
        return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
    if not (is_admin(request.user) or property.owner == request.user):
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
        property.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


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
        if not (is_landlord(request.user) and property.owner == request.user):
            return Response({'detail': 'Only landlords can add units to their properties.'}, status=status.HTTP_403_FORBIDDEN)
        serializer = UnitSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(property=property, created_by=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def unit_detail(request, pk):
    try:
        unit = Unit.objects.get(pk=pk)
    except Unit.DoesNotExist:
        return Response({'detail': 'Unit not found.'}, status=status.HTTP_404_NOT_FOUND)
    if not (is_admin(request.user) or unit.property.owner == request.user):
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
        unit.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


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
        if not (is_landlord(request.user) and unit.property.owner == request.user):
            return Response({'detail': 'Only landlords can add images.'}, status=status.HTTP_403_FORBIDDEN)
        serializer = PropertyImageSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(property=unit.property)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def lease_list_create(request, unit_id):
    try:
        unit = Unit.objects.get(pk=unit_id)
    except Unit.DoesNotExist:
        return Response({'detail': 'Unit not found.'}, status=status.HTTP_404_NOT_FOUND)
    if request.method == 'GET':
        lease = getattr(unit, 'lease', None)
        if lease:
            serializer = LeaseSerializer(lease)
            return Response(serializer.data)
        return Response({'detail': 'No lease for this unit.'}, status=status.HTTP_404_NOT_FOUND)
    elif request.method == 'POST':
        if not (is_landlord(request.user) and unit.property.owner == request.user):
            return Response({'detail': 'Only landlords can assign tenants.'}, status=status.HTTP_403_FORBIDDEN)
        serializer = LeaseSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(unit=unit)
            unit.is_occupied = True
            unit.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([AllowAny])
def public_units(request):
    units = Unit.objects.filter(is_occupied=False, is_public=True)
    serializer = UnitSerializer(units, many=True)
    return Response(serializer.data)
