from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema, OpenApiExample

from authentication.models import Role
from property.models import Property
from .models import NeighborhoodInsight
from .serializers import NeighborhoodInsightSerializer


def _can_add_insight(user, prop):
    """Landlord who owns the property, assigned agent, or admin."""
    if user.is_staff:
        return True
    if user.role and user.role.name == Role.LANDLORD and prop.owner == user:
        return True
    if user.role and user.role.name == Role.AGENT:
        return prop.property_agents.filter(agent=user).exists()
    return False


@extend_schema(
    methods=['GET'],
    summary="List neighborhood insights for a property",
)
@extend_schema(
    methods=['POST'],
    summary="Add a neighborhood insight to a property",
    examples=[
        OpenApiExample(
            "Add school",
            request_only=True,
            value={
                "insight_type": "school",
                "name": "Westlands Primary School",
                "address": "Westlands Road, Nairobi",
                "distance_km": "0.8",
                "rating": "4.2",
                "lat": "-1.268250",
                "lng": "36.811900",
                "notes": "Government school with good KCPE results",
            },
        ),
        OpenApiExample(
            "Add hospital",
            request_only=True,
            value={
                "insight_type": "hospital",
                "name": "Aga Khan University Hospital",
                "address": "3rd Parklands Ave, Nairobi",
                "distance_km": "2.1",
                "rating": "4.7",
                "lat": "-1.261800",
                "lng": "36.816300",
                "notes": "Level 6 hospital with 24/7 A&E",
            },
        ),
    ],
)
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def insight_list(request, property_pk):
    try:
        prop = Property.objects.get(pk=property_pk)
    except Property.DoesNotExist:
        return Response({'error': 'Property not found.'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        insight_type = request.query_params.get('type')
        qs = NeighborhoodInsight.objects.filter(property=prop).select_related('added_by')
        if insight_type:
            qs = qs.filter(insight_type=insight_type)
        return Response(NeighborhoodInsightSerializer(qs, many=True).data)

    if not _can_add_insight(request.user, prop):
        return Response({'detail': 'Only the property owner, assigned agent, or admin can add insights.'}, status=status.HTTP_403_FORBIDDEN)

    serializer = NeighborhoodInsightSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(property=prop, added_by=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(methods=['GET'], summary="Get a neighborhood insight")
@extend_schema(
    methods=['PATCH'],
    summary="Update a neighborhood insight",
    examples=[
        OpenApiExample(
            "Update insight",
            request_only=True,
            value={"rating": "4.5", "notes": "Renovated in 2025"},
        )
    ],
)
@extend_schema(methods=['DELETE'], summary="Delete a neighborhood insight")
@api_view(['GET', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def insight_detail(request, property_pk, insight_pk):
    try:
        insight = NeighborhoodInsight.objects.select_related('property', 'added_by').get(
            pk=insight_pk, property__pk=property_pk
        )
    except NeighborhoodInsight.DoesNotExist:
        return Response({'error': 'Insight not found.'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        return Response(NeighborhoodInsightSerializer(insight).data)

    is_adder = insight.added_by == request.user
    is_admin = request.user.is_staff
    if not (is_adder or is_admin):
        return Response({'detail': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)

    if request.method == 'PATCH':
        serializer = NeighborhoodInsightSerializer(insight, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    elif request.method == 'DELETE':
        insight.delete()
        return Response({'deleted': True}, status=status.HTTP_204_NO_CONTENT)
