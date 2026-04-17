from rest_framework.throttling import UserRateThrottle


class MessagingParticipantsThrottle(UserRateThrottle):
    """Limits abusive directory scraping on GET /api/messaging/participants/."""

    rate = '120/min'
