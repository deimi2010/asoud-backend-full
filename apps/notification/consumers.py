"""
Enhanced WebSocket Consumer for Notifications
Real-time notification delivery system
"""

from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.utils import timezone
import json
import logging

from apps.notification.validator import validate_user
from apps.notification.models import Notification

User = get_user_model()
logger = logging.getLogger(__name__)


class NotificationConsumer(AsyncWebsocketConsumer):
    """
    Enhanced WebSocket consumer for real-time notifications
    """
    
    async def connect(self):
        """Handle WebSocket connection"""
        try:
            logger.info("Connecting to notification system")
            
            # Authenticate user
            user = await validate_user(self.scope)
            
            if user is None or not user.is_authenticated:
                logger.warning("Unauthenticated user attempted to connect")
                await self.close()
                return
            
            self.scope["user"] = user
            self.user_id = user.id
            self.user_groups = [f"user_{user.id}"]
            
            # Accept connection
            await self.accept()
            
            # Add to user group
            await self.channel_layer.group_add(f"user_{user.id}", self.channel_name)
            
            # Add to owner group if applicable
            if await self._is_owner(user):
                await self.channel_layer.group_add("owners", self.channel_name)
                self.user_groups.append("owners")
                logger.info(f"Owner {user.id} added to owners group")
            
            # Send connection confirmation
            await self.send(text_data=json.dumps({
                'type': 'connection_established',
                'message': 'Connected to notification system',
                'user_id': user.id,
                'timestamp': timezone.now().isoformat()
            }))
            
            logger.info(f"User {user.id} connected to notification system")
            
        except Exception as e:
            logger.error(f"Error in WebSocket connect: {e}")
            await self.close()
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        try:
            user = self.scope.get("user")
            if user and user.is_authenticated:
                # Remove from all groups
                for group in self.user_groups:
                    await self.channel_layer.group_discard(group, self.channel_name)
                
                logger.info(f"User {user.id} disconnected from notification system")
        except Exception as e:
            logger.error(f"Error in WebSocket disconnect: {e}")
    
    async def receive(self, text_data):
        """Handle incoming WebSocket messages"""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'ping':
                # Respond to ping with pong
                await self.send(text_data=json.dumps({
                    'type': 'pong',
                    'timestamp': timezone.now().isoformat()
                }))
            
            elif message_type == 'mark_as_read':
                # Mark notification as read
                notification_id = data.get('notification_id')
                if notification_id:
                    await self._mark_notification_as_read(notification_id)
            
            elif message_type == 'get_unread_count':
                # Get unread notification count
                count = await self._get_unread_count()
                await self.send(text_data=json.dumps({
                    'type': 'unread_count',
                    'count': count,
                    'timestamp': timezone.now().isoformat()
                }))
            
            else:
                logger.warning(f"Unknown message type: {message_type}")
                
        except json.JSONDecodeError:
            logger.error("Invalid JSON received")
        except Exception as e:
            logger.error(f"Error processing WebSocket message: {e}")
    
    async def send_notification(self, event):
        """Send notification to WebSocket client"""
        try:
            data = event.get('data', {})
            
            # Add timestamp if not present
            if 'timestamp' not in data:
                data['timestamp'] = timezone.now().isoformat()
            
            # Send notification
            await self.send(text_data=json.dumps(data))
            
            # Mark as delivered if notification ID is provided
            notification_id = data.get('id')
            if notification_id:
                await self._mark_notification_as_delivered(notification_id)
            
            logger.info(f"Notification sent to user {self.user_id}: {data.get('title', 'No title')}")
            
        except Exception as e:
            logger.error(f"Error sending notification: {e}")
    
    async def send_system_message(self, event):
        """Send system message to WebSocket client"""
        try:
            data = event.get('data', {})
            data['type'] = 'system_message'
            data['timestamp'] = timezone.now().isoformat()
            
            await self.send(text_data=json.dumps(data))
            
        except Exception as e:
            logger.error(f"Error sending system message: {e}")
    
    async def send_owner_message(self, event):
        """Send owner-specific message to WebSocket client"""
        try:
            data = event.get('data', {})
            data['type'] = 'owner_message'
            data['timestamp'] = timezone.now().isoformat()
            
            await self.send(text_data=json.dumps(data))
            
        except Exception as e:
            logger.error(f"Error sending owner message: {e}")
    
    @database_sync_to_async
    def _is_owner(self, user):
        """Check if user is an owner"""
        try:
            return user.is_owner()
        except:
            return False
    
    @database_sync_to_async
    def _mark_notification_as_read(self, notification_id):
        """Mark notification as read"""
        try:
            notification = Notification.objects.get(
                id=notification_id,
                user_id=self.user_id
            )
            notification.mark_as_read()
            logger.info(f"Notification {notification_id} marked as read")
        except Notification.DoesNotExist:
            logger.warning(f"Notification {notification_id} not found for user {self.user_id}")
        except Exception as e:
            logger.error(f"Error marking notification as read: {e}")
    
    @database_sync_to_async
    def _mark_notification_as_delivered(self, notification_id):
        """Mark notification as delivered"""
        try:
            notification = Notification.objects.get(
                id=notification_id,
                user_id=self.user_id
            )
            notification.mark_as_delivered()
            logger.info(f"Notification {notification_id} marked as delivered")
        except Notification.DoesNotExist:
            logger.warning(f"Notification {notification_id} not found for user {self.user_id}")
        except Exception as e:
            logger.error(f"Error marking notification as delivered: {e}")
    
    @database_sync_to_async
    def _get_unread_count(self):
        """Get unread notification count for user"""
        try:
            return Notification.objects.filter(
                user_id=self.user_id,
                status__in=[Notification.SENT, Notification.DELIVERED]
            ).count()
        except Exception as e:
            logger.error(f"Error getting unread count: {e}")
            return 0