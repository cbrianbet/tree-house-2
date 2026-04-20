def create_notification(
    user,
    notification_type,
    title,
    body,
    action_url='',
    *,
    email_pref_key=None,
):
    """
    Creates an in-app Notification record.
    Also sends an email if the user's NotificationPreference allows it.

    notification_type must be one of the Notification.NOTIFICATION_TYPES values (e.g. message, maintenance, payment, payment_reminder, lease, dispute, application, …).

    email_pref_key: optional NotificationPreference field name (snake_case) to gate email
    for this specific notification. When set, it overrides the default mapping for
    notification_type.
    """
    from .models import Notification
    notification = Notification.objects.create(
        user=user,
        notification_type=notification_type,
        title=title,
        body=body,
        action_url=action_url,
    )
    _maybe_send_email(user, notification_type, title, body, email_pref_key=email_pref_key)
    return notification


def _maybe_send_email(user, notification_type, title, body, *, email_pref_key=None):
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

    if email_pref_key is not None:
        should_send = getattr(prefs, email_pref_key, True)
    else:
        should_send = _default_email_allowed(prefs, notification_type)

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


def _default_email_allowed(prefs, notification_type):
    """Map notification_type to preference flag(s) when email_pref_key is not passed."""
    if notification_type == 'message':
        return prefs.direct_message_received
    if notification_type == 'maintenance':
        return prefs.maintenance_updates
    if notification_type == 'payment':
        return prefs.payment_received
    if notification_type == 'payment_reminder':
        return prefs.payment_due_reminder
    if notification_type == 'lease':
        return prefs.lease_expiry_notice
    if notification_type == 'dispute':
        return prefs.dispute_status_change or prefs.dispute_new_message
    if notification_type == 'application':
        return prefs.new_application or prefs.application_status_change
    # new_listing, moving, account, … — no dedicated toggles yet
    return True
