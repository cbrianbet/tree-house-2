from dj_rest_auth.registration.views import (
    ResendEmailVerificationView,
    VerifyEmailView,
)
from dj_rest_auth.views import (
    PasswordChangeView,
    PasswordResetConfirmView,
    PasswordResetView,
)
from authentication.views import email_confirm_redirect, password_reset_confirm_redirect
from dj_rest_auth.registration.views import RegisterView
from dj_rest_auth.views import LoginView, LogoutView, UserDetailsView
from django.urls import path
from drf_spectacular.utils import extend_schema, OpenApiExample
from .views import (
    role_list, role_detail,
    tenant_profile_list, tenant_profile_detail,
    landlord_profile_list, landlord_profile_detail,
    agent_profile_list, agent_profile_detail,
    artisan_profile_list, artisan_profile_detail,
    moving_company_profile_list, moving_company_profile_detail,
    me_account, me_profile, me_notifications,
)

_register_view = extend_schema(
    summary="Register a new user",
    examples=[
        OpenApiExample(
            "Register",
            request_only=True,
            value={
                "username": "johndoe",
                "email": "john@example.com",
                "password1": "StrongPass!123",
                "password2": "StrongPass!123",
                "first_name": "John",
                "last_name": "Doe",
                "phone": "0712345678",
                "role": 1,
            },
        )
    ],
)(RegisterView)

_login_view = extend_schema(
    summary="Login and receive auth token",
    examples=[
        OpenApiExample(
            "Login",
            request_only=True,
            value={"username": "johndoe", "password": "StrongPass!123"},
        )
    ],
)(LoginView)

_password_reset_view = extend_schema(
    summary="Request password reset email",
    examples=[
        OpenApiExample(
            "Password reset",
            request_only=True,
            value={"email": "john@example.com"},
        )
    ],
)(PasswordResetView)

_password_reset_confirm_view = extend_schema(
    summary="Confirm password reset",
    examples=[
        OpenApiExample(
            "Password reset confirm",
            request_only=True,
            value={
                "new_password1": "NewPass!456",
                "new_password2": "NewPass!456",
                "uid": "MQ",
                "token": "abc123-tokenstring",
            },
        )
    ],
)(PasswordResetConfirmView)


urlpatterns = [
    path("register/", _register_view.as_view(), name="rest_register"),
    path("login/", _login_view.as_view(), name="rest_login"),
    path("logout/", LogoutView.as_view(), name="rest_logout"),
    path("user/", UserDetailsView.as_view(), name="rest_user_details"),
	
    #todo: Work on this later with company email
    path("register/verify-email/", VerifyEmailView.as_view(), name="rest_verify_email"),
    path("register/resend-email/", ResendEmailVerificationView.as_view(), name="rest_resend_email"),
    path("account-confirm-email/<str:key>/", email_confirm_redirect, name="account_confirm_email"),
    path("account-confirm-email/", VerifyEmailView.as_view(), name="account_email_verification_sent"),
    path("password/reset/", _password_reset_view.as_view(), name="rest_password_reset"),
    path(
        "password/reset/confirm/<str:uidb64>/<str:token>/",
        password_reset_confirm_redirect,
        name="password_reset_confirm",
    ),
    path("password/reset/confirm/", _password_reset_confirm_view.as_view(), name="password_reset_confirm"),

    path('roles/', role_list, name='role-list'),
    path('roles/<int:pk>/', role_detail, name='role-detail'),

    path('profiles/tenant/', tenant_profile_list, name='tenant-profile-list'),
    path('profiles/tenant/<int:pk>/', tenant_profile_detail, name='tenant-profile-detail'),

    path('profiles/landlord/', landlord_profile_list, name='landlord-profile-list'),
    path('profiles/landlord/<int:pk>/', landlord_profile_detail, name='landlord-profile-detail'),

    path('profiles/agent/', agent_profile_list, name='agent-profile-list'),
    path('profiles/agent/<int:pk>/', agent_profile_detail, name='agent-profile-detail'),

    path('profiles/artisan/', artisan_profile_list, name='artisan-profile-list'),
    path('profiles/artisan/<int:pk>/', artisan_profile_detail, name='artisan-profile-detail'),

    path('profiles/moving-company/', moving_company_profile_list, name='moving-company-profile-list'),
    path('profiles/moving-company/<int:pk>/', moving_company_profile_detail, name='moving-company-profile-detail'),

    # Current user self-service
    path('me/', me_account, name='me-account'),
    path('me/profile/', me_profile, name='me-profile'),
    path('me/notifications/', me_notifications, name='me-notifications'),
    path('password/change/', PasswordChangeView.as_view(), name='rest_password_change'),
]