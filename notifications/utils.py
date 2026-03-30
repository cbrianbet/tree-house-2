def create_notification(user, notification_type, title, body, action_url=''):
    """
    Creates an in-app Notification record.
    Also sends an email if the user's NotificationPreference allows it.

    notification_type must be one of: message, maintenance, payment, lease, dispute, application
    """
    from .models import Notification
    notification = Notification.objects.create(
        user=user,
        notification_type=notification_type,
        title=title,
        body=body,
        action_url=action_url,
    )
    _maybe_send_email(user, notification_type, title, body)
    return notification


def _maybe_send_email(user, notification_type, title, body):
    """Send email if user's NotificationPreference allows it for this type."""
    from authentication.models import NotificationPreference
    from django.core.mail import send_mail
    from django.conf import settings

    try:
        prefs = NotificationPreference.objects.get(user=user)
    except NotificationPreference.DoesNotExist:
        # No prefs saved yet — treat as all-enabled (default behaviour)
        prefs = None

    if prefs is not None and not prefs.email_notifications:
        return

    # Map notification_type to preference flag (None prefs = all True)
    type_to_pref = {
        'message': True,
        'maintenance': prefs.maintenance_updates if prefs else True,
        'payment': prefs.payment_received if prefs else True,
        'lease': prefs.lease_expiry_notice if prefs else True,
        'dispute': True,
        'application': prefs.application_status_change if prefs else True,
    }

    should_send = type_to_pref.get(notification_type, True)
    if not should_send:
        return

    try:
        send_mail(
            subject=title,
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=True,
        )
    except Exception:
        pass  # never let email failures break the request
