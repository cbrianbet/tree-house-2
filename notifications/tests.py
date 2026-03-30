from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from authentication.models import NotificationPreference, Role
from .models import Notification
from .utils import create_notification

User = get_user_model()


# ── Helper ───────────────────────────────────────────────────────────────────

def make_user(username, role_name):
    role, _ = Role.objects.get_or_create(name=role_name)
    user = User.objects.create_user(username=username, password='testpass', role=role)
    token = Token.objects.create(user=user)
    return user, token


# ── List ─────────────────────────────────────────────────────────────────────

class NotificationListTests(APITestCase):

    def setUp(self):
        self.user, self.token = make_user('tenant1', 'Tenant')
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')
        # 2 unread + 1 read
        Notification.objects.create(
            user=self.user, notification_type='payment',
            title='Payment due', body='Your rent is due.', is_read=False,
        )
        Notification.objects.create(
            user=self.user, notification_type='lease',
            title='Lease expiring', body='Your lease expires soon.', is_read=False,
        )
        Notification.objects.create(
            user=self.user, notification_type='message',
            title='Hello', body='Hi there.', is_read=True,
        )

    def test_list_own_notifications(self):
        url = reverse('notification-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)

    def test_unread_filter(self):
        url = reverse('notification-list') + '?unread=true'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        for item in response.data:
            self.assertFalse(item['is_read'])

    def test_cannot_see_others_notifications(self):
        other_user, _ = make_user('landlord1', 'Landlord')
        Notification.objects.create(
            user=other_user, notification_type='application',
            title='New application', body='Someone applied.', is_read=False,
        )
        url = reverse('notification-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Still only sees own 3 notifications
        self.assertEqual(len(response.data), 3)

    def test_unauthenticated(self):
        self.client.credentials()
        url = reverse('notification-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


# ── Mark single read ──────────────────────────────────────────────────────────

class NotificationMarkReadTests(APITestCase):

    def setUp(self):
        self.user, self.token = make_user('tenant2', 'Tenant')
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')
        self.notification = Notification.objects.create(
            user=self.user, notification_type='maintenance',
            title='Request updated', body='Your maintenance request was updated.',
            is_read=False,
        )

    def test_mark_read(self):
        url = reverse('notification-mark-read', args=[self.notification.pk])
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['is_read'])
        self.notification.refresh_from_db()
        self.assertTrue(self.notification.is_read)

    def test_cannot_mark_others_notification(self):
        other_user, _ = make_user('landlord2', 'Landlord')
        other_notif = Notification.objects.create(
            user=other_user, notification_type='payment',
            title='Payment received', body='A payment was received.',
            is_read=False,
        )
        url = reverse('notification-mark-read', args=[other_notif.pk])
        response = self.client.post(url)
        # Returns 404 to avoid leaking existence
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_mark_nonexistent(self):
        url = reverse('notification-mark-read', args=[99999])
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_unauthenticated(self):
        self.client.credentials()
        url = reverse('notification-mark-read', args=[self.notification.pk])
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


# ── Read-all ──────────────────────────────────────────────────────────────────

class NotificationReadAllTests(APITestCase):

    def setUp(self):
        self.user, self.token = make_user('tenant3', 'Tenant')
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')
        for i in range(3):
            Notification.objects.create(
                user=self.user, notification_type='message',
                title=f'Message {i}', body=f'Body {i}.', is_read=False,
            )

    def test_read_all(self):
        url = reverse('notification-read-all')
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('detail', response.data)
        self.assertEqual(Notification.objects.filter(user=self.user, is_read=False).count(), 0)

    def test_read_all_idempotent(self):
        url = reverse('notification-read-all')
        self.client.post(url)
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Notification.objects.filter(user=self.user, is_read=False).count(), 0)

    def test_read_all_does_not_affect_other_users(self):
        other_user, _ = make_user('landlord3', 'Landlord')
        other_notif = Notification.objects.create(
            user=other_user, notification_type='application',
            title='App', body='Body.', is_read=False,
        )
        url = reverse('notification-read-all')
        self.client.post(url)
        other_notif.refresh_from_db()
        self.assertFalse(other_notif.is_read)

    def test_unauthenticated(self):
        self.client.credentials()
        url = reverse('notification-read-all')
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


# ── Utility function ──────────────────────────────────────────────────────────

class CreateNotificationUtilTests(APITestCase):

    def setUp(self):
        self.user, _ = make_user('tenant4', 'Tenant')

    def test_create_notification_creates_record(self):
        notification = create_notification(
            user=self.user,
            notification_type='payment',
            title='Payment received',
            body='Your payment of KES 10,000 was confirmed.',
            action_url='/invoices/1/',
        )
        self.assertIsNotNone(notification.pk)
        self.assertEqual(notification.user, self.user)
        self.assertEqual(notification.notification_type, 'payment')
        self.assertEqual(notification.title, 'Payment received')
        self.assertFalse(notification.is_read)
        db_record = Notification.objects.get(pk=notification.pk)
        self.assertEqual(db_record.action_url, '/invoices/1/')

    def test_create_notification_no_email_when_no_prefs(self):
        """Without a NotificationPreference record, no email is sent."""
        with patch('django.core.mail.send_mail') as mock_send:
            create_notification(
                user=self.user,
                notification_type='payment',
                title='Payment',
                body='Body.',
            )
            mock_send.assert_not_called()

    def test_create_notification_sends_email_when_prefs_enabled(self):
        """Email is sent when email_notifications=True and the type flag is on."""
        NotificationPreference.objects.create(
            user=self.user,
            email_notifications=True,
            payment_received=True,
        )
        with patch('django.core.mail.send_mail') as mock_send:
            create_notification(
                user=self.user,
                notification_type='payment',
                title='Payment received',
                body='Body.',
            )
            mock_send.assert_called_once()

    def test_create_notification_respects_email_pref_disabled(self):
        """No email when email_notifications=False."""
        NotificationPreference.objects.create(
            user=self.user,
            email_notifications=False,
        )
        with patch('django.core.mail.send_mail') as mock_send:
            create_notification(
                user=self.user,
                notification_type='payment',
                title='Payment',
                body='Body.',
            )
            mock_send.assert_not_called()

    def test_create_notification_respects_type_pref_disabled(self):
        """No email when email_notifications=True but the specific type flag is False."""
        NotificationPreference.objects.create(
            user=self.user,
            email_notifications=True,
            maintenance_updates=False,
        )
        with patch('django.core.mail.send_mail') as mock_send:
            create_notification(
                user=self.user,
                notification_type='maintenance',
                title='Maintenance update',
                body='Body.',
            )
            mock_send.assert_not_called()

    def test_create_notification_default_action_url(self):
        """action_url defaults to empty string."""
        notification = create_notification(
            user=self.user,
            notification_type='message',
            title='Hi',
            body='Hello.',
        )
        self.assertEqual(notification.action_url, '')
