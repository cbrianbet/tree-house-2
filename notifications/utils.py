def create_notification(user, notification_type, title, body, action_url=''):
    """
    Creates an in-app Notification record.
    Also sends an email if the user's NotificationPreference allows it.

    notification_type must be one of the Notification.NOTIFICATION_TYPES values (e.g. message, maintenance, payment, payment_reminder, lease, dispute, application, …).
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
        # No prefs record yet — require explicit opt-in, so skip email
        return

    if not prefs.email_notifications:
        return

    # Map notification_type to preference flag
    type_to_pref = {
        'message': True,  # always send message notifications if email_notifications is on
        'maintenance': prefs.maintenance_updates,
        'payment': prefs.payment_received,
        'payment_reminder': prefs.payment_due_reminder,
        'lease': prefs.lease_expiry_notice,
        'dispute': True,  # always send dispute notifications
        'application': prefs.application_status_change,
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
