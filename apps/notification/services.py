"""
Advanced Notification Services for ASOUD Platform
Comprehensive notification system with multiple channels
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from django.utils import timezone
from django.template import Template, Context
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q

from .models import (
    Notification, NotificationTemplate, NotificationPreference,
    NotificationLog, NotificationQueue
)

User = get_user_model()
logger = logging.getLogger(__name__)


class NotificationService:
    """
    Main notification service for handling all notification operations
    """
    
    def __init__(self):
        self.providers = {
            'push': PushNotificationProvider(),
            'email': EmailNotificationProvider(),
            'sms': SMSNotificationProvider(),
            'websocket': WebSocketNotificationProvider(),
        }
    
    def send_notification(
        self,
        user: User,
        notification_type: str,
        title: str,
        body: str,
        channel: str = 'websocket',
        data: Optional[Dict] = None,
        priority: str = 'medium',
        scheduled_at: Optional[datetime] = None,
        content_object=None
    ) -> bool:
        """
        Send a notification to a user
        
        Args:
            user: Target user
            notification_type: Type of notification
            title: Notification title
            body: Notification body
            channel: Delivery channel (push, email, sms, websocket)
            data: Additional data
            priority: Notification priority
            scheduled_at: When to send (None for immediate)
            content_object: Related object
            
        Returns:
            bool: Success status
        """
        try:
            # Check user preferences
            if not self._should_send_notification(user, notification_type, channel):
                logger.info(f"Notification skipped due to user preferences: {user.id}")
                return False
            
            # Create notification record
            notification = self._create_notification(
                user=user,
                notification_type=notification_type,
                title=title,
                body=body,
                channel=channel,
                data=data or {},
                priority=priority,
                scheduled_at=scheduled_at,
                content_object=content_object
            )
            
            if scheduled_at:
                self._add_to_queue(notification)
                return True

            # Immediate delivery is not also queued; that previously caused a
            # second send when the queue processor ran.
            success = self._process_notification(notification)
            if not success and notification.can_retry():
                self._add_to_queue(notification)
                return True  # Accepted for asynchronous retry.
            return success
            
        except Exception as e:
            logger.error(f"Error sending notification: {e}")
            return False
    
    def send_bulk_notifications(
        self,
        users: List[User],
        notification_type: str,
        title: str,
        body: str,
        channel: str = 'websocket',
        data: Optional[Dict] = None,
        priority: str = 'medium',
        scheduled_at: Optional[datetime] = None
    ) -> Dict[str, int]:
        """
        Send notifications to multiple users
        
        Returns:
            Dict with success/failure counts
        """
        results = {'success': 0, 'failed': 0}
        
        for user in users:
            try:
                success = self.send_notification(
                    user=user,
                    notification_type=notification_type,
                    title=title,
                    body=body,
                    channel=channel,
                    data=data,
                    priority=priority,
                    scheduled_at=scheduled_at
                )
                
                if success:
                    results['success'] += 1
                else:
                    results['failed'] += 1
                    
            except Exception as e:
                logger.error(f"Error sending bulk notification to user {user.id}: {e}")
                results['failed'] += 1
        
        return results
    
    def send_template_notification(
        self,
        user: User,
        template_name: str,
        context: Optional[Dict] = None,
        channel: str = 'websocket',
        priority: str = 'medium',
        scheduled_at: Optional[datetime] = None,
        content_object=None
    ) -> bool:
        """
        Send notification using a template
        
        Args:
            user: Target user
            template_name: Template name
            context: Template context variables
            channel: Delivery channel
            priority: Notification priority
            scheduled_at: When to send
            content_object: Related object
            
        Returns:
            bool: Success status
        """
        try:
            # Get template
            template = NotificationTemplate.objects.get(
                name=template_name,
                channel=channel,
                is_active=True
            )
            
            # Render template
            rendered = self._render_template(template, context or {})
            
            # Send notification
            return self.send_notification(
                user=user,
                notification_type=template.notification_type,
                title=rendered['title'],
                body=rendered['body'],
                channel=channel,
                data=rendered.get('data', {}),
                priority=priority,
                scheduled_at=scheduled_at,
                content_object=content_object
            )
            
        except NotificationTemplate.DoesNotExist:
            logger.error(f"Template not found: {template_name}")
            return False
        except Exception as e:
            logger.error(f"Error sending template notification: {e}")
            return False
    
    def _create_notification(
        self,
        user: User,
        notification_type: str,
        title: str,
        body: str,
        channel: str,
        data: Dict,
        priority: str,
        scheduled_at: Optional[datetime],
        content_object=None
    ) -> Notification:
        """Create notification record"""
        
        # Get or create content type
        content_type = None
        object_id = None
        if content_object:
            content_type = type(content_object)._meta
            object_id = content_object.pk
        
        notification = Notification.objects.create(
            user=user,
            notification_type=notification_type,
            channel=channel,
            title=title,
            body=body,
            data=data,
            priority=priority,
            scheduled_at=scheduled_at,
            content_type=content_type,
            object_id=object_id
        )
        
        return notification
    
    def _add_to_queue(self, notification: Notification):
        """Add notification to processing queue"""
        scheduled_at = notification.scheduled_at or timezone.now()
        
        # Calculate priority score
        priority_score = self._calculate_priority_score(notification)
        
        NotificationQueue.objects.create(
            notification=notification,
            priority=priority_score,
            scheduled_at=scheduled_at
        )
    
    def _calculate_priority_score(self, notification: Notification) -> int:
        """Calculate priority score for queue ordering"""
        base_score = {
            'high': 100,
            'medium': 50,
            'low': 10
        }.get(notification.priority, 50)
        
        # Add channel priority
        channel_priority = {
            'sms': 20,
            'push': 15,
            'email': 10,
            'websocket': 5
        }.get(notification.channel, 10)
        
        return base_score + channel_priority
    
    def _should_send_notification(self, user: User, notification_type: str, channel: str) -> bool:
        """Check if notification should be sent based on user preferences"""
        try:
            prefs = user.notification_preferences
        except NotificationPreference.DoesNotExist:
            # Create default preferences
            prefs = NotificationPreference.objects.create(user=user)
        
        # Check if channel is enabled
        channel_enabled = getattr(prefs, f'{channel}_enabled', False)
        if not channel_enabled:
            return False
        
        # Check type-specific preferences
        type_mapping = {
            'order_confirmed': 'orders',
            'payment_success': 'orders',
            'new_message': 'messages',
            'market_approved': 'system',
            'product_published': 'system',
            'discount_available': 'marketing',
            'system_maintenance': 'system',
            'security_alert': 'system'
        }
        
        pref_type = type_mapping.get(notification_type, 'system')
        type_enabled = getattr(prefs, f'{channel}_{pref_type}', True)
        
        if not type_enabled:
            return False
        
        # Check quiet hours
        if self._is_quiet_hours(prefs):
            return False
        
        return True
    
    def _is_quiet_hours(self, prefs: NotificationPreference) -> bool:
        """Check if current time is within quiet hours"""
        if not prefs.quiet_hours_start or not prefs.quiet_hours_end:
            return False
        
        now = timezone.now().time()
        start = prefs.quiet_hours_start
        end = prefs.quiet_hours_end
        
        if start <= end:
            return start <= now <= end
        else:
            # Quiet hours span midnight
            return now >= start or now <= end
    
    def _render_template(self, template: NotificationTemplate, context: Dict) -> Dict:
        """Render notification template with context"""
        try:
            # Render title
            title_template = Template(template.title)
            rendered_title = title_template.render(Context(context))
            
            # Render body
            body_template = Template(template.body)
            rendered_body = body_template.render(Context(context))
            
            return {
                'title': rendered_title,
                'body': rendered_body,
                'data': context
            }
            
        except Exception as e:
            logger.error(f"Error rendering template {template.name}: {e}")
            return {
                'title': template.title,
                'body': template.body,
                'data': context
            }
    
    def _process_notification(self, notification: Notification) -> bool:
        """Process a single notification"""
        try:
            provider = self.providers.get(notification.channel)
            if not provider:
                logger.error(f"No provider found for channel: {notification.channel}")
                return False
            
            # Log attempt
            start_time = time.time()
            attempt_number = notification.retry_count + 1
            
            # Send notification
            success = provider.send(notification)
            
            # Calculate duration
            duration_ms = int((time.time() - start_time) * 1000)
            
            # Log result
            NotificationLog.objects.create(
                notification=notification,
                attempt_number=attempt_number,
                status=Notification.SENT if success else Notification.FAILED,
                duration_ms=duration_ms,
                error_message=None if success else "Provider send failed"
            )
            
            if success:
                notification.mark_as_sent()
                return True
            else:
                notification.increment_retry()
                if notification.can_retry():
                    # Reschedule for retry
                    retry_delay = min(300, 60 * (2 ** notification.retry_count))  # Exponential backoff
                    notification.scheduled_at = timezone.now() + timedelta(seconds=retry_delay)
                    notification.save()
                else:
                    notification.mark_as_failed("Max retries exceeded")
                return False
                
        except Exception as e:
            logger.error(f"Error processing notification {notification.id}: {e}")
            notification.mark_as_failed(str(e))
            return False


class BaseNotificationProvider:
    """Base class for notification providers"""
    
    def send(self, notification: Notification) -> bool:
        """Send notification - to be implemented by subclasses"""
        raise NotImplementedError


class PushNotificationProvider(BaseNotificationProvider):
    """Firebase Cloud Messaging provider"""
    
    def send(self, notification: Notification) -> bool:
        """Send push notification via Firebase"""
        logger.warning("Push provider is not configured")
        return False


class EmailNotificationProvider(BaseNotificationProvider):
    """Email notification provider"""
    
    def send(self, notification: Notification) -> bool:
        """Send email notification"""
        logger.warning("Email provider is not configured")
        return False


class SMSNotificationProvider(BaseNotificationProvider):
    """SMS notification provider"""
    
    def send(self, notification: Notification) -> bool:
        """Send SMS notification"""
        logger.warning("SMS notification provider is not configured")
        return False


class WebSocketNotificationProvider(BaseNotificationProvider):
    """WebSocket notification provider"""
    
    def send(self, notification: Notification) -> bool:
        """Send WebSocket notification"""
        try:
            from channels.layers import get_channel_layer
            from asgiref.sync import async_to_sync
            
            channel_layer = get_channel_layer()
            
            # Send to user's personal channel
            async_to_sync(channel_layer.group_send)(
                f"user_{notification.user.id}",
                {
                    'type': 'send_notification',
                    'data': {
                        'id': str(notification.id),
                        'type': notification.notification_type,
                        'title': notification.title,
                        'body': notification.body,
                        'data': notification.data,
                        'timestamp': notification.created_at.isoformat()
                    }
                }
            )
            
            logger.info(f"WebSocket notification sent: {notification.title}")
            return True
            
        except Exception as e:
            logger.error(f"WebSocket notification failed: {e}")
            return False


class NotificationQueueProcessor:
    """Process queued notifications"""
    
    def __init__(self):
        self.service = NotificationService()
    
    def process_queue(self, batch_size: int = 100) -> Dict[str, int]:
        """Process queued notifications"""
        results = {'processed': 0, 'failed': 0}
        now = timezone.now()
        stale_before = now - timedelta(minutes=5)

        # Claim work under short row locks, then perform provider I/O after the
        # transaction commits. Stale claims are recoverable after five minutes.
        with transaction.atomic():
            queued_notifications = list(
                NotificationQueue.objects.select_for_update(skip_locked=True)
                .filter(
                    Q(is_processing=False)
                    | Q(is_processing=True, processing_started_at__lt=stale_before),
                    scheduled_at__lte=now,
                )
                .select_related('notification')[:batch_size]
            )
            for queue_entry in queued_notifications:
                queue_entry.mark_as_processing()

        for queue_entry in queued_notifications:
            try:
                success = self.service._process_notification(queue_entry.notification)
                with transaction.atomic():
                    locked_entry = (
                        NotificationQueue.objects.select_for_update()
                        .select_related('notification')
                        .get(id=queue_entry.id)
                    )

                    if success:
                        results['processed'] += 1
                        locked_entry.delete()
                    else:
                        results['failed'] += 1
                        notification = locked_entry.notification
                        if notification.can_retry():
                            locked_entry.scheduled_at = notification.scheduled_at
                            locked_entry.is_processing = False
                            locked_entry.processing_started_at = None
                            locked_entry.save(
                                update_fields=[
                                    'scheduled_at',
                                    'is_processing',
                                    'processing_started_at',
                                ]
                            )
                        else:
                            locked_entry.delete()

            except NotificationQueue.DoesNotExist:
                continue
            except Exception:
                logger.exception("Notification queue entry processing failed")
                results['failed'] += 1
                NotificationQueue.objects.filter(id=queue_entry.id).delete()
        
        return results
    
    def cleanup_old_notifications(self, days: int = 30):
        """Clean up old notifications"""
        cutoff_date = timezone.now() - timedelta(days=days)
        
        # Delete old notifications
        deleted_count, _ = Notification.objects.filter(
            created_at__lt=cutoff_date,
            status__in=[Notification.DELIVERED, Notification.READ, Notification.FAILED]
        ).delete()
        
        logger.info(f"Cleaned up {deleted_count} old notifications")
        return deleted_count

