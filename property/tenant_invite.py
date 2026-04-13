import hashlib
import secrets
from django.conf import settings
from django.core.mail import send_mail


def hash_invite_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode('utf-8')).hexdigest()


def new_invite_token() -> str:
    return secrets.token_urlsafe(32)


def send_tenant_invitation_email(to_email: str, raw_token: str, property_name: str, unit_name: str) -> None:
    base = getattr(
        settings,
        'TENANT_INVITE_REDIRECT_BASE_URL',
        'http://localhost:8000/tenant-invite/',
    ).rstrip('/')
    invite_url = f"{base}?token={raw_token}"
    subject = 'Complete your Tree House tenant account'
    message = (
        f"You have been invited to rent {unit_name} at {property_name}.\n\n"
        f"Complete your profile and set your password here:\n{invite_url}\n\n"
        f"If you did not expect this email, you can ignore it."
    )
    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[to_email],
        fail_silently=True,
    )


def send_existing_tenant_lease_email(to_email: str, property_name: str, unit_name: str) -> None:
    subject = 'New lease on Tree House'
    message = (
        f"A lease has been created for you for {unit_name} at {property_name}.\n\n"
        f"Log in to your Tree House account to view details."
    )
    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[to_email],
        fail_silently=True,
    )
