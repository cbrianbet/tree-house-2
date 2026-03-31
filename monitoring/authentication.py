from rest_framework.authentication import TokenAuthentication
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied


class ImpersonatingTokenAuthentication(TokenAuthentication):
    """
    Extends standard token auth to support admin impersonation.

    Usage: include the header on any request:
        X-Impersonate-User: <target_user_pk>

    Rules:
    - The requester must be an active admin (is_staff=True).
    - The target user must be active and non-admin.
    - Every impersonated request is written to ImpersonationLog.
    - request._impersonating_admin is set so views can inspect it if needed.
    """

    def authenticate(self, request):
        result = super().authenticate(request)
        if result is None:
            return None

        user, token = result
        target_pk = request.META.get('HTTP_X_IMPERSONATE_USER')

        if not target_pk:
            return result

        if not user.is_staff:
            raise PermissionDenied('Only admins can impersonate users.')

        from django.contrib.auth import get_user_model
        User = get_user_model()

        try:
            target = User.objects.get(pk=target_pk, is_active=True)
        except (User.DoesNotExist, ValueError):
            raise AuthenticationFailed('Target user not found or inactive.')

        if target.is_staff:
            raise PermissionDenied('Cannot impersonate another admin.')

        self._write_log(user, target, request)

        request._impersonating_admin = user
        return (target, token)

    def _write_log(self, admin, target, request):
        from monitoring.models import ImpersonationLog
        ImpersonationLog.objects.create(
            admin=admin,
            target_user=target,
            path=request.path,
            method=request.method,
        )
