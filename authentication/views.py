from django.conf import settings
from django.http import HttpResponseRedirect
from django.http import HttpResponseRedirect
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema, OpenApiExample

from .serializers import RoleSerializer, TenantProfileSerializer, LandlordProfileSerializer, AgentProfileSerializer
from .models import Role, TenantProfile, LandlordProfile, AgentProfile


def email_confirm_redirect(request, key):
    return HttpResponseRedirect(
        f"{settings.EMAIL_CONFIRM_REDIRECT_BASE_URL}{key}/"
    )


def password_reset_confirm_redirect(request, uidb64, token):
    return HttpResponseRedirect(
        f"{settings.PASSWORD_RESET_CONFIRM_REDIRECT_BASE_URL}{uidb64}/{token}/"
    )


@extend_schema(
    methods=['GET'],
    summary="List all roles",
)
@extend_schema(
    methods=['POST'],
    summary="Create a role",
    examples=[
        OpenApiExample(
            "Create role",
            value={"name": "Tenant", "description": "Rents properties"},
            request_only=True,
        )
    ],
)
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def role_list(request):
    if request.method == 'GET':
        roles = Role.objects.all()
        serializer = RoleSerializer(roles, many=True)
        return Response(serializer.data)
    elif request.method == 'POST':
        serializer = RoleSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(methods=['GET'], summary="Get a role")
@extend_schema(
    methods=['PUT'],
    summary="Update a role",
    examples=[
        OpenApiExample(
            "Update role",
            value={"name": "SuperAdmin", "description": "Updated description"},
            request_only=True,
        )
    ],
)
@extend_schema(methods=['DELETE'], summary="Delete a role")
@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def role_detail(request, pk):
    try:
        role = Role.objects.get(pk=pk)
    except Role.DoesNotExist:
        return Response({'error': 'Role not found'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        serializer = RoleSerializer(role)
        return Response(serializer.data)
    elif request.method == 'PUT':
        serializer = RoleSerializer(role, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    elif request.method == 'DELETE':
        role.delete()
        return Response({'deleted': True}, status=status.HTTP_204_NO_CONTENT)


def _profile_list_view(model, serializer_class):
    @api_view(['GET', 'POST'])
    @permission_classes([IsAuthenticated])
    def view(request):
        if request.method == 'GET':
            profiles = model.objects.select_related('user').all()
            serializer = serializer_class(profiles, many=True)
            return Response(serializer.data)
        elif request.method == 'POST':
            serializer = serializer_class(data=request.data)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    return view


def _profile_detail_view(model, serializer_class):
    @api_view(['GET', 'PUT', 'DELETE'])
    @permission_classes([IsAuthenticated])
    def view(request, pk):
        try:
            profile = model.objects.get(pk=pk)
        except model.DoesNotExist:
            return Response({'error': 'Not found'}, status=status.HTTP_404_NOT_FOUND)

        if request.method == 'GET':
            serializer = serializer_class(profile)
            return Response(serializer.data)
        elif request.method == 'PUT':
            serializer = serializer_class(profile, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        elif request.method == 'DELETE':
            profile.delete()
            return Response({'deleted': True}, status=status.HTTP_204_NO_CONTENT)
    return view


tenant_profile_list = extend_schema(methods=['GET'], summary="List tenant profiles")(
    extend_schema(
        methods=['POST'],
        summary="Create tenant profile",
        examples=[OpenApiExample("Create", request_only=True, value={
            "user": 1,
            "national_id": "12345678",
            "emergency_contact_name": "Jane Doe",
            "emergency_contact_phone": "0722000000",
        })],
    )(_profile_list_view(TenantProfile, TenantProfileSerializer))
)

tenant_profile_detail = extend_schema(methods=['GET'], summary="Get tenant profile")(
    extend_schema(
        methods=['PUT'],
        summary="Update tenant profile",
        examples=[OpenApiExample("Update", request_only=True, value={
            "national_id": "99999999",
            "emergency_contact_phone": "0733000000",
        })],
    )(
        extend_schema(methods=['DELETE'], summary="Delete tenant profile")(
            _profile_detail_view(TenantProfile, TenantProfileSerializer)
        )
    )
)

landlord_profile_list = extend_schema(methods=['GET'], summary="List landlord profiles")(
    extend_schema(
        methods=['POST'],
        summary="Create landlord profile",
        examples=[OpenApiExample("Create", request_only=True, value={
            "user": 2,
            "company_name": "Bett Properties Ltd",
            "tax_id": "A123456789B",
            "verified": False,
        })],
    )(_profile_list_view(LandlordProfile, LandlordProfileSerializer))
)

landlord_profile_detail = extend_schema(methods=['GET'], summary="Get landlord profile")(
    extend_schema(
        methods=['PUT'],
        summary="Update landlord profile",
        examples=[OpenApiExample("Update", request_only=True, value={
            "verified": True,
            "company_name": "Updated Co.",
        })],
    )(
        extend_schema(methods=['DELETE'], summary="Delete landlord profile")(
            _profile_detail_view(LandlordProfile, LandlordProfileSerializer)
        )
    )
)

agent_profile_list = extend_schema(methods=['GET'], summary="List agent profiles")(
    extend_schema(
        methods=['POST'],
        summary="Create agent profile",
        examples=[OpenApiExample("Create", request_only=True, value={
            "user": 3,
            "agency_name": "Top Agents Ltd",
            "license_number": "LIC-2024-001",
            "commission_rate": "5.00",
        })],
    )(_profile_list_view(AgentProfile, AgentProfileSerializer))
)

agent_profile_detail = extend_schema(methods=['GET'], summary="Get agent profile")(
    extend_schema(
        methods=['PUT'],
        summary="Update agent profile",
        examples=[OpenApiExample("Update", request_only=True, value={
            "commission_rate": "7.50",
            "license_number": "LIC-2024-002",
        })],
    )(
        extend_schema(methods=['DELETE'], summary="Delete agent profile")(
            _profile_detail_view(AgentProfile, AgentProfileSerializer)
        )
    )
)
