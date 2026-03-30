from django.conf import settings
from django.http import HttpResponseRedirect
from django.http import HttpResponseRedirect
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema, OpenApiExample

from .serializers import (
    RoleSerializer, TenantProfileSerializer, LandlordProfileSerializer,
    AgentProfileSerializer, ArtisanProfileSerializer,
    AccountUpdateSerializer, NotificationPreferenceSerializer,
)
from .models import Role, TenantProfile, LandlordProfile, AgentProfile, ArtisanProfile, NotificationPreference, CustomUser


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
@permission_classes([AllowAny])
def role_list(request):
    if request.method == 'GET':
        # Exclude Admin from public listing — it is not a self-assignable role
        roles = Role.objects.exclude(name=Role.ADMIN)
        serializer = RoleSerializer(roles, many=True)
        return Response(serializer.data)
    elif request.method == 'POST':
        if not (request.user.is_authenticated and request.user.is_staff):
            return Response({'detail': 'Admin access required.'}, status=status.HTTP_403_FORBIDDEN)
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

    if not request.user.is_staff:
        return Response({'detail': 'Admin access required.'}, status=status.HTTP_403_FORBIDDEN)

    if request.method == 'PUT':
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
            if not request.user.is_staff:
                return Response({'detail': 'Admin access required.'}, status=status.HTTP_403_FORBIDDEN)
            profiles = model.objects.select_related('user').all()
            serializer = serializer_class(profiles, many=True)
            return Response(serializer.data)
        elif request.method == 'POST':
            if not request.user.is_staff:
                return Response({'detail': 'Admin access required.'}, status=status.HTTP_403_FORBIDDEN)
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

        is_owner = profile.user == request.user
        if not (is_owner or request.user.is_staff):
            return Response({'detail': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)

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

artisan_profile_list = extend_schema(methods=['GET'], summary="List artisan profiles")(
    extend_schema(
        methods=['POST'],
        summary="Create artisan profile",
        examples=[OpenApiExample("Create", request_only=True, value={
            "user": 5,
            "trade": "plumbing",
            "bio": "10 years experience in residential plumbing",
        })],
    )(_profile_list_view(ArtisanProfile, ArtisanProfileSerializer))
)

artisan_profile_detail = extend_schema(methods=['GET'], summary="Get artisan profile")(
    extend_schema(
        methods=['PUT'],
        summary="Update artisan profile",
        examples=[OpenApiExample("Update", request_only=True, value={
            "bio": "Updated bio",
            "verified": True,
        })],
    )(
        extend_schema(methods=['DELETE'], summary="Delete artisan profile")(
            _profile_detail_view(ArtisanProfile, ArtisanProfileSerializer)
        )
    )
)


# ---------------------------------------------------------------------------
# "Me" endpoints — always operate on the authenticated user's own data
# ---------------------------------------------------------------------------

_ROLE_PROFILE_MAP = {
    Role.TENANT: (TenantProfile, TenantProfileSerializer),
    Role.LANDLORD: (LandlordProfile, LandlordProfileSerializer),
    Role.AGENT: (AgentProfile, AgentProfileSerializer),
    Role.ARTISAN: (ArtisanProfile, ArtisanProfileSerializer),
}


@extend_schema(
    methods=['GET'],
    summary="Get current user's account details",
)
@extend_schema(
    methods=['PATCH'],
    summary="Partially update current user's account details",
    examples=[
        OpenApiExample(
            "Update account",
            request_only=True,
            value={
                "first_name": "John",
                "last_name": "Doe",
                "email": "john@example.com",
                "phone": "0712345678",
            },
        )
    ],
)
@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated])
def me_account(request):
    if request.method == 'GET':
        serializer = AccountUpdateSerializer(request.user)
        return Response(serializer.data)
    serializer = AccountUpdateSerializer(request.user, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    methods=['GET'],
    summary="Get current user's role-specific profile",
)
@extend_schema(
    methods=['PATCH'],
    summary="Partially update current user's role-specific profile",
    examples=[
        OpenApiExample(
            "Update tenant profile",
            request_only=True,
            value={"national_id": "12345678", "emergency_contact_name": "Jane Doe", "emergency_contact_phone": "0722000000"},
        ),
        OpenApiExample(
            "Update landlord profile",
            request_only=True,
            value={"company_name": "Bett Properties Ltd", "tax_id": "A123456789B"},
        ),
        OpenApiExample(
            "Update agent profile",
            request_only=True,
            value={"agency_name": "Top Agents Ltd", "commission_rate": "5.00"},
        ),
        OpenApiExample(
            "Update artisan profile",
            request_only=True,
            value={"trade": "plumbing", "bio": "10 years experience"},
        ),
    ],
)
@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated])
def me_profile(request):
    role_name = request.user.role.name if request.user.role else None
    mapping = _ROLE_PROFILE_MAP.get(role_name)
    if not mapping:
        return Response({'detail': 'No role-specific profile for this user.'}, status=status.HTTP_404_NOT_FOUND)

    model, serializer_class = mapping
    profile, _ = model.objects.get_or_create(user=request.user)

    if request.method == 'GET':
        return Response(serializer_class(profile).data)

    serializer = serializer_class(profile, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    methods=['GET'],
    summary="Get current user's notification preferences",
)
@extend_schema(
    methods=['PATCH'],
    summary="Partially update current user's notification preferences",
    examples=[
        OpenApiExample(
            "Update notifications",
            request_only=True,
            value={
                "email_notifications": True,
                "payment_due_reminder": True,
                "payment_received": False,
                "maintenance_updates": True,
                "new_maintenance_request": True,
                "new_application": True,
                "application_status_change": True,
                "lease_expiry_notice": True,
            },
        )
    ],
)
@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated])
def me_notifications(request):
    prefs, _ = NotificationPreference.objects.get_or_create(user=request.user)

    if request.method == 'GET':
        return Response(NotificationPreferenceSerializer(prefs).data)

    serializer = NotificationPreferenceSerializer(prefs, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
