from rest_framework.authentication import BaseAuthentication, TokenAuthentication
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied


class QueryParameterTokenAuthentication(BaseAuthentication):
    """
    Authenticates using ?token=<key> against the DRF authtoken Token model.

    Browser navigations (e.g. opening a file URL in a new tab) do not send
    Authorization headers; append the token as a query parameter for those cases.
    Invalid tokens raise AuthenticationFailed; missing token returns None so other
    authenticators (e.g. header-based Token auth) can run.
    """

    def authenticate(self, request):
        key = request.query_params.get('token')
        if not key:
            return None
        from rest_framework.authtoken.models import Token

        try:
            token = Token.objects.select_related('user').get(key=key)
        except Token.DoesNotExist:
            raise AuthenticationFailed('Invalid token.')
        if not token.user.is_active:
            raise AuthenticationFailed('User inactive or deleted.')
        return (token.user, token)

    def authenticate_header(self, request):
        # Must match TokenAuthentication so APIView does not coerce 401 → 403 when
        # authenticate_header() would otherwise be None (DRF uses authenticators[0]).
        return 'Token'


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
