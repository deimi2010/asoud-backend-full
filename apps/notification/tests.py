"""
Tests for notification app
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase, APIRequestFactory, force_authenticate
from rest_framework import status

from .models import Notification, NotificationQueue
from .services import NotificationService, PushNotificationProvider
from .views import NotificationViewSet
from unittest.mock import Mock, patch

User = get_user_model()


class NotificationContainmentTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('09120000121', None)

    def test_regular_user_cannot_create_notification_for_another_user(self):
        target = User.objects.create_user('09120000122', None)
        request = APIRequestFactory().post(
            '/notifications/',
            {
                'user_id': target.id,
                'notification_type': 'security_alert',
                'title': 'fake system notice',
                'body': 'fake',
                'channel': 'websocket',
            },
            format='json',
        )
        force_authenticate(request, user=self.user)

        response = NotificationViewSet.as_view({'post': 'create'})(request)

        self.assertEqual(response.status_code, 403)
        self.assertFalse(Notification.objects.exists())

    def test_unconfigured_push_provider_reports_failure(self):
        self.assertFalse(PushNotificationProvider().send(Mock()))

    @patch.object(NotificationService, '_process_notification', return_value=True)
    @patch.object(NotificationService, '_create_notification')
    @patch.object(NotificationService, '_should_send_notification', return_value=True)
    def test_immediate_notification_is_not_also_queued(self, _, create, process):
        notification = Mock()
        create.return_value = notification
        service = NotificationService()
        service._add_to_queue = Mock()

        success = service.send_notification(
            user=self.user,
            notification_type='security_alert',
            title='title',
            body='body',
        )

        self.assertTrue(success)
        process.assert_called_once_with(notification)
        service._add_to_queue.assert_not_called()

    @patch.object(NotificationService, '_process_notification', return_value=False)
    @patch.object(NotificationService, '_create_notification')
    @patch.object(NotificationService, '_should_send_notification', return_value=True)
    def test_failed_immediate_notification_is_queued_for_retry(self, _, create, process):
        notification = Mock()
        notification.can_retry.return_value = True
        create.return_value = notification
        service = NotificationService()
        service._add_to_queue = Mock()

        success = service.send_notification(
            user=self.user,
            notification_type='security_alert',
            title='title',
            body='body',
        )

        self.assertTrue(success)
        process.assert_called_once_with(notification)
        service._add_to_queue.assert_called_once_with(notification)

    @patch.object(NotificationService, 'send_notification', return_value=True)
    def test_admin_create_reports_accepted_to_prevent_client_retry_duplicates(self, send):
        admin = User.objects.create_user('09120000123', None, is_staff=True)
        request = APIRequestFactory().post(
            '/notifications/',
            {
                'user_id': self.user.id,
                'notification_type': 'security_alert',
                'title': 'system notice',
                'body': 'body',
                'channel': 'websocket',
            },
            format='json',
        )
        force_authenticate(request, user=admin)

        response = NotificationViewSet.as_view({'post': 'create'})(request)

        self.assertEqual(response.status_code, 202)
        send.assert_called_once()

    def test_completed_queue_entry_is_terminal(self):
        notification = Notification.objects.create(
            user=self.user,
            notification_type='security_alert',
            channel='websocket',
            title='title',
            body='body',
        )
        queue_entry = NotificationQueue.objects.create(
            notification=notification,
            scheduled_at=timezone.now(),
        )

        queue_entry.mark_as_completed()

        self.assertFalse(NotificationQueue.objects.filter(id=queue_entry.id).exists())


class NotificationModelTests(TestCase):
    """Test notification models"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            mobile_number='09123456789',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_notification_creation(self):
        """Test notification creation"""
        notification = Notification.objects.create(
            user=self.user,
            notification_type='order_confirmed',
            channel='push',
            title='Test Notification',
            body='This is a test notification',
            priority='high'
        )
        
        self.assertEqual(notification.user, self.user)
        self.assertEqual(notification.notification_type, 'order_confirmed')
        self.assertEqual(notification.channel, 'push')
        self.assertEqual(notification.status, 'pending')
        self.assertEqual(notification.priority, 'high')
    
    def test_notification_mark_as_sent(self):
        """Test marking notification as sent"""
        notification = Notification.objects.create(
            user=self.user,
            notification_type='order_confirmed',
            channel='push',
            title='Test Notification',
            body='This is a test notification'
        )
        
        notification.mark_as_sent()
        
        self.assertEqual(notification.status, 'sent')
        self.assertIsNotNone(notification.sent_at)


class NotificationAPITests(APITestCase):
    """Test notification API endpoints"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            mobile_number='09123456789',
            email='test@example.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)
    
    def test_notification_list(self):
        """Test notification list endpoint"""
        # Create test notifications
        Notification.objects.create(
            user=self.user,
            notification_type='order_confirmed',
            channel='push',
            title='Test Notification 1',
            body='This is test notification 1'
        )
        
        response = self.client.get('/api/v1/notifications/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Check if response is paginated or not
        if isinstance(response.data, dict) and 'results' in response.data:
            self.assertEqual(len(response.data['results']), 1)
        else:
            self.assertEqual(len(response.data), 1)
