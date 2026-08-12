"""
Advanced WebSocket Consumers for Chat and Support System
Real-time chat messaging with file sharing and support tickets
"""

import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
import base64
import mimetypes
import uuid

from .models import (
    ChatRoom, ChatMessage, ChatParticipant, SupportTicket,
    chat_user_display_name,
)
from .services import ChatService, SupportService

User = get_user_model()
logger = logging.getLogger(__name__)


class ChatConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time chat messaging
    """
    
    async def connect(self):
        """Handle WebSocket connection"""
        try:
            # Get user from scope
            self.user = self.scope["user"]
            
            if not self.user or not self.user.is_authenticated:
                await self.close()
                return
            
            # Get room ID from URL
            self.room_id = self.scope['url_route']['kwargs']['room_id']
            
            # Verify room exists and user is participant
            room = await self.get_room(self.room_id)
            if not room:
                await self.close()
                return
            
            if not await self.is_participant(room, self.user):
                await self.close()
                return
            
            # Join room group
            self.room_group_name = f"chat_{self.room_id}"
            await self.channel_layer.group_add(
                self.room_group_name,
                self.channel_name
            )
            
            # Accept connection
            await self.accept()
            
            # Send connection confirmation
            await self.send(text_data=json.dumps({
                'type': 'connection_established',
                'message': 'Connected to chat room',
                'room_id': self.room_id,
                'user_id': self.user.id,
                'timestamp': timezone.now().isoformat()
            }))
            
            # Send recent messages
            await self.send_recent_messages(room)
            
            # Notify other participants about user joining
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'user_joined',
                    'user_id': self.user.id,
                    'username': chat_user_display_name(self.user),
                    'timestamp': timezone.now().isoformat()
                }
            )
            
            logger.info("User %s connected to chat room %s", self.user.pk, self.room_id)
            
        except Exception as e:
            logger.error(f"Error in WebSocket connect: {e}")
            await self.close()
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        try:
            if hasattr(self, 'room_group_name'):
                # Notify other participants about user leaving
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'user_left',
                        'user_id': self.user.id,
                        'username': chat_user_display_name(self.user),
                        'timestamp': timezone.now().isoformat()
                    }
                )
                
                # Leave room group
                await self.channel_layer.group_discard(
                    self.room_group_name,
                    self.channel_name
                )
            
            logger.info("User %s disconnected from chat room %s", self.user.pk, self.room_id)
            
        except Exception as e:
            logger.error(f"Error in WebSocket disconnect: {e}")
    
    async def receive(self, text_data):
        """Handle incoming WebSocket messages"""
        try:
            room = await self.get_room(self.room_id)
            if not room or not await self.is_participant(room, self.user):
                await self.send(text_data=json.dumps({
                    'type': 'membership_revoked',
                    'room_id': self.room_id,
                }))
                await self.close(code=4403)
                return
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'chat_message':
                await self.handle_chat_message(data)
            elif message_type == 'typing':
                await self.handle_typing(data)
            elif message_type == 'stop_typing':
                await self.handle_stop_typing(data)
            elif message_type == 'mark_as_read':
                await self.handle_mark_as_read(data)
            elif message_type == 'ping':
                await self.handle_ping()
            else:
                logger.warning(f"Unknown message type: {message_type}")
                
        except json.JSONDecodeError:
            logger.error("Invalid JSON received")
        except Exception as e:
            logger.error(f"Error processing WebSocket message: {e}")
    
    async def handle_chat_message(self, data):
        """Handle chat message"""
        try:
            content = data.get('content', '').strip()
            message_type = data.get('message_type', 'text')
            reply_to_id = data.get('reply_to_id')
            file_data = data.get('file_data')
            
            if not content and not file_data:
                return
            
            # Get room
            room = await self.get_room(self.room_id)
            if not room:
                return
            
            # Prepare message data
            message_data = {
                'content': content,
                'message_type': message_type,
            }
            
            # Handle file upload
            if file_data and message_type in ['image', 'file', 'audio', 'video']:
                file_info = await self.process_file_upload(file_data)
                if file_info:
                    message_data.update(file_info)
            
            # Handle reply
            if reply_to_id:
                reply_to = await self.get_message(reply_to_id)
                if reply_to:
                    message_data['reply_to'] = reply_to
            
            # Create message
            message = await self.create_message(room, message_data)
            
            if message:
                # Send message to room group
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'chat_message',
                        'message': {
                            'id': str(message.id),
                            'sender_id': message.sender.id,
                            'sender_username': chat_user_display_name(message.sender),
                            'content': message.content,
                            'message_type': message.message_type,
                            'file_name': message.file_name,
                            'file_size': message.file_size,
                            'file_type': message.file_type,
                            'reply_to': {
                                'id': str(message.reply_to.id),
                                'content': message.reply_to.content[:50] + '...' if len(message.reply_to.content) > 50 else message.reply_to.content,
                                'sender_username': chat_user_display_name(message.reply_to.sender),
                            } if message.reply_to else None,
                            'sent_at': message.sent_at.isoformat(),
                            'status': message.status,
                        }
                    }
                )
                
                logger.info(f"Message {message.id} sent to room {self.room_id}")
            
        except Exception as e:
            logger.error(f"Error handling chat message: {e}")
    
    async def handle_typing(self, data):
        """Handle typing indicator"""
        try:
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'typing',
                    'user_id': self.user.id,
                    'username': chat_user_display_name(self.user),
                    'timestamp': timezone.now().isoformat()
                }
            )
        except Exception as e:
            logger.error(f"Error handling typing: {e}")
    
    async def handle_stop_typing(self, data):
        """Handle stop typing indicator"""
        try:
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'stop_typing',
                    'user_id': self.user.id,
                    'username': chat_user_display_name(self.user),
                    'timestamp': timezone.now().isoformat()
                }
            )
        except Exception as e:
            logger.error(f"Error handling stop typing: {e}")
    
    async def handle_mark_as_read(self, data):
        """Handle mark message as read"""
        try:
            message_id = data.get('message_id')
            if message_id:
                message = await self.get_message(message_id)
                if message:
                    await self.mark_message_as_read(message)
        except Exception as e:
            logger.error(f"Error handling mark as read: {e}")
    
    async def handle_ping(self):
        """Handle ping message"""
        try:
            await self.send(text_data=json.dumps({
                'type': 'pong',
                'timestamp': timezone.now().isoformat()
            }))
        except Exception as e:
            logger.error(f"Error handling ping: {e}")
    
    async def chat_message(self, event):
        """Send chat message to WebSocket"""
        try:
            message = event['message']
            await self.send(text_data=json.dumps({
                'type': 'chat_message',
                'message': message
            }))
        except Exception as e:
            logger.error(f"Error sending chat message: {e}")
    
    async def typing(self, event):
        """Send typing indicator to WebSocket"""
        try:
            await self.send(text_data=json.dumps({
                'type': 'typing',
                'user_id': event['user_id'],
                'username': event['username'],
                'timestamp': event['timestamp']
            }))
        except Exception as e:
            logger.error(f"Error sending typing indicator: {e}")
    
    async def stop_typing(self, event):
        """Send stop typing indicator to WebSocket"""
        try:
            await self.send(text_data=json.dumps({
                'type': 'stop_typing',
                'user_id': event['user_id'],
                'username': event['username'],
                'timestamp': event['timestamp']
            }))
        except Exception as e:
            logger.error(f"Error sending stop typing indicator: {e}")
    
    async def user_joined(self, event):
        """Send user joined notification to WebSocket"""
        try:
            await self.send(text_data=json.dumps({
                'type': 'user_joined',
                'user_id': event['user_id'],
                'username': event['username'],
                'timestamp': event['timestamp']
            }))
        except Exception as e:
            logger.error(f"Error sending user joined notification: {e}")
    
    async def user_left(self, event):
        """Send user left notification to WebSocket"""
        try:
            await self.send(text_data=json.dumps({
                'type': 'user_left',
                'user_id': event['user_id'],
                'username': event['username'],
                'timestamp': event['timestamp']
            }))
        except Exception as e:
            logger.error(f"Error sending user left notification: {e}")

    async def membership_revoked(self, event):
        """Immediately evict a removed member from an already-open socket."""
        if str(event.get('user_id')) != str(self.user.pk):
            return
        await self.send(text_data=json.dumps({
            'type': 'membership_revoked',
            'room_id': self.room_id,
        }))
        await self.close(code=4403)

    async def membership_updated(self, event):
        """Push role/capability changes without requiring a reconnect."""
        await self.send(text_data=json.dumps({
            'type': 'membership_updated',
            'room_id': self.room_id,
            'user_id': event.get('user_id'),
            'role': event.get('role'),
        }))
    
    @database_sync_to_async
    def get_room(self, room_id):
        """Get chat room by ID"""
        try:
            return ChatRoom.objects.get(id=room_id)
        except ChatRoom.DoesNotExist:
            return None
    
    @database_sync_to_async
    def is_participant(self, room, user):
        """Check if user is participant in room"""
        return room.is_participant(user)
    
    @database_sync_to_async
    def get_message(self, message_id):
        """Get message by ID"""
        try:
            return ChatMessage.objects.get(id=message_id)
        except ChatMessage.DoesNotExist:
            return None
    
    @database_sync_to_async
    def create_message(self, room, message_data):
        """Create new message"""
        try:
            chat_service = ChatService()
            return chat_service.send_message(
                chat_room=room,
                sender=self.user,
                **message_data
            )
        except Exception as e:
            logger.error(f"Error creating message: {e}")
            return None
    
    @database_sync_to_async
    def mark_message_as_read(self, message):
        """Mark message as read"""
        try:
            chat_service = ChatService()
            return chat_service.mark_message_as_read(message, self.user)
        except Exception as e:
            logger.error(f"Error marking message as read: {e}")
            return False
    
    async def send_recent_messages(self, room):
        """Send recent messages to user"""
        try:
            chat_service = ChatService()
            messages = await database_sync_to_async(chat_service.get_messages)(room, self.user, 20)
            
            for message in messages:
                await self.send(text_data=json.dumps({
                    'type': 'chat_message',
                    'message': {
                        'id': str(message.id),
                        'sender_id': message.sender.id,
                        'sender_username': chat_user_display_name(message.sender),
                        'content': message.content,
                        'message_type': message.message_type,
                        'file_name': message.file_name,
                        'file_size': message.file_size,
                        'file_type': message.file_type,
                        'reply_to': {
                            'id': str(message.reply_to.id),
                            'content': message.reply_to.content[:50] + '...' if len(message.reply_to.content) > 50 else message.reply_to.content,
                            'sender_username': chat_user_display_name(message.reply_to.sender),
                        } if message.reply_to else None,
                        'sent_at': message.sent_at.isoformat(),
                        'status': message.status,
                    }
                }))
        except Exception as e:
            logger.error(f"Error sending recent messages: {e}")
    
    async def process_file_upload(self, file_data):
        """Process file upload from base64 data"""
        try:
            if not file_data:
                return None
            
            # Decode base64 data
            file_content = base64.b64decode(file_data['content'])
            file_name = file_data.get('name', f"file_{uuid.uuid4().hex}")
            file_type = file_data.get('type', 'application/octet-stream')
            
            # Create file object
            file_obj = ContentFile(file_content, name=file_name)
            
            return {
                'file': file_obj,
                'file_name': file_name,
                'file_size': len(file_content),
                'file_type': file_type,
            }
            
        except Exception as e:
            logger.error(f"Error processing file upload: {e}")
            return None


class SupportConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for support ticket chat
    """
    
    async def connect(self):
        """Handle WebSocket connection"""
        try:
            # Get user from scope
            self.user = self.scope["user"]
            
            if not self.user or not self.user.is_authenticated:
                await self.close()
                return
            
            # Get ticket ID from URL
            self.ticket_id = self.scope['url_route']['kwargs']['ticket_id']
            
            # Verify ticket exists and user has access
            ticket = await self.get_ticket(self.ticket_id)
            if not ticket:
                await self.close()
                return
            
            if not await self.has_ticket_access(ticket, self.user):
                await self.close()
                return
            
            # Join ticket group
            self.ticket_group_name = f"support_{self.ticket_id}"
            await self.channel_layer.group_add(
                self.ticket_group_name,
                self.channel_name
            )
            
            # Accept connection
            await self.accept()
            
            # Send connection confirmation
            await self.send(text_data=json.dumps({
                'type': 'connection_established',
                'message': 'Connected to support ticket',
                'ticket_id': self.ticket_id,
                'ticket_number': ticket.ticket_number,
                'user_id': self.user.id,
                'timestamp': timezone.now().isoformat()
            }))
            
            # Send recent messages
            await self.send_recent_messages(ticket.chat_room)
            
            # Notify other participants about user joining
            await self.channel_layer.group_send(
                self.ticket_group_name,
                {
                    'type': 'user_joined',
                    'user_id': self.user.id,
                    'username': chat_user_display_name(self.user),
                    'timestamp': timezone.now().isoformat()
                }
            )
            
            logger.info("User %s connected to support ticket %s", self.user.pk, ticket.ticket_number)
            
        except Exception as e:
            logger.error(f"Error in WebSocket connect: {e}")
            await self.close()
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        try:
            if hasattr(self, 'ticket_group_name'):
                # Notify other participants about user leaving
                await self.channel_layer.group_send(
                    self.ticket_group_name,
                    {
                        'type': 'user_left',
                        'user_id': self.user.id,
                        'username': chat_user_display_name(self.user),
                        'timestamp': timezone.now().isoformat()
                    }
                )
                
                # Leave ticket group
                await self.channel_layer.group_discard(
                    self.ticket_group_name,
                    self.channel_name
                )
            
            logger.info("User %s disconnected from support ticket %s", self.user.pk, self.ticket_id)
            
        except Exception as e:
            logger.error(f"Error in WebSocket disconnect: {e}")
    
    async def receive(self, text_data):
        """Handle incoming WebSocket messages"""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'support_message':
                await self.handle_support_message(data)
            elif message_type == 'ticket_status_update':
                await self.handle_ticket_status_update(data)
            elif message_type == 'ping':
                await self.handle_ping()
            else:
                logger.warning(f"Unknown message type: {message_type}")
                
        except json.JSONDecodeError:
            logger.error("Invalid JSON received")
        except Exception as e:
            logger.error(f"Error processing WebSocket message: {e}")
    
    async def handle_support_message(self, data):
        """Handle support message"""
        try:
            content = data.get('content', '').strip()
            message_type = data.get('message_type', 'text')
            
            if not content:
                return
            
            # Get ticket
            ticket = await self.get_ticket(self.ticket_id)
            if not ticket:
                return
            
            # Create message
            message = await self.create_message(ticket.chat_room, {
                'content': content,
                'message_type': message_type,
            })
            
            if message:
                # Update ticket activity
                await self.update_ticket_activity(ticket)
                
                # Send message to ticket group
                await self.channel_layer.group_send(
                    self.ticket_group_name,
                    {
                        'type': 'support_message',
                        'message': {
                            'id': str(message.id),
                            'sender_id': message.sender.id,
                            'sender_username': chat_user_display_name(message.sender),
                            'content': message.content,
                            'message_type': message.message_type,
                            'sent_at': message.sent_at.isoformat(),
                            'status': message.status,
                        }
                    }
                )
                
                logger.info(f"Support message {message.id} sent to ticket {ticket.ticket_number}")
            
        except Exception as e:
            logger.error(f"Error handling support message: {e}")
    
    async def handle_ticket_status_update(self, data):
        """Handle ticket status update"""
        try:
            status = data.get('status')
            resolution = data.get('resolution', '')
            
            if not status:
                return
            
            # Get ticket
            ticket = await self.get_ticket(self.ticket_id)
            if not ticket:
                return
            
            # Check if user can update status
            if not await self.can_update_ticket_status(ticket, self.user):
                return
            
            # Update ticket status
            await self.update_ticket_status(ticket, status, resolution)
            
            # Notify all participants
            await self.channel_layer.group_send(
                self.ticket_group_name,
                {
                    'type': 'ticket_status_updated',
                    'ticket_id': str(ticket.id),
                    'ticket_number': ticket.ticket_number,
                    'status': status,
                    'resolution': resolution,
                    'updated_by': chat_user_display_name(self.user),
                    'timestamp': timezone.now().isoformat()
                }
            )
            
            logger.info(f"Ticket {ticket.ticket_number} status updated to {status}")
            
        except Exception as e:
            logger.error(f"Error handling ticket status update: {e}")
    
    async def handle_ping(self):
        """Handle ping message"""
        try:
            await self.send(text_data=json.dumps({
                'type': 'pong',
                'timestamp': timezone.now().isoformat()
            }))
        except Exception as e:
            logger.error(f"Error handling ping: {e}")
    
    async def support_message(self, event):
        """Send support message to WebSocket"""
        try:
            message = event['message']
            await self.send(text_data=json.dumps({
                'type': 'support_message',
                'message': message
            }))
        except Exception as e:
            logger.error(f"Error sending support message: {e}")
    
    async def ticket_status_updated(self, event):
        """Send ticket status update to WebSocket"""
        try:
            await self.send(text_data=json.dumps({
                'type': 'ticket_status_updated',
                'ticket_id': event['ticket_id'],
                'ticket_number': event['ticket_number'],
                'status': event['status'],
                'resolution': event['resolution'],
                'updated_by': event['updated_by'],
                'timestamp': event['timestamp']
            }))
        except Exception as e:
            logger.error(f"Error sending ticket status update: {e}")
    
    async def user_joined(self, event):
        """Send user joined notification to WebSocket"""
        try:
            await self.send(text_data=json.dumps({
                'type': 'user_joined',
                'user_id': event['user_id'],
                'username': event['username'],
                'timestamp': event['timestamp']
            }))
        except Exception as e:
            logger.error(f"Error sending user joined notification: {e}")
    
    async def user_left(self, event):
        """Send user left notification to WebSocket"""
        try:
            await self.send(text_data=json.dumps({
                'type': 'user_left',
                'user_id': event['user_id'],
                'username': event['username'],
                'timestamp': event['timestamp']
            }))
        except Exception as e:
            logger.error(f"Error sending user left notification: {e}")
    
    @database_sync_to_async
    def get_ticket(self, ticket_id):
        """Get support ticket by ID"""
        try:
            return SupportTicket.objects.select_related(
                'chat_room', 'user', 'assigned_to'
            ).get(id=ticket_id)
        except SupportTicket.DoesNotExist:
            return None
    
    @database_sync_to_async
    def has_ticket_access(self, ticket, user):
        """Check if user has access to ticket"""
        return (
            ticket.user == user or
            ticket.assigned_to == user or
            user.is_staff
        )
    
    @database_sync_to_async
    def can_update_ticket_status(self, ticket, user):
        """Check if user can update ticket status"""
        return (
            ticket.assigned_to == user or
            user.is_staff
        )
    
    @database_sync_to_async
    def create_message(self, room, message_data):
        """Create new message"""
        try:
            chat_service = ChatService()
            return chat_service.send_message(
                chat_room=room,
                sender=self.user,
                **message_data
            )
        except Exception as e:
            logger.error(f"Error creating message: {e}")
            return None
    
    @database_sync_to_async
    def update_ticket_activity(self, ticket):
        """Update ticket last activity"""
        ticket.update_activity()
    
    @database_sync_to_async
    def update_ticket_status(self, ticket, status, resolution):
        """Update ticket status"""
        try:
            if status == 'resolved':
                ticket.resolve(resolution)
            elif status == 'closed':
                ticket.close()
            else:
                ticket.status = status
                ticket.save(update_fields=['status'])
        except Exception as e:
            logger.error(f"Error updating ticket status: {e}")
    
    async def send_recent_messages(self, room):
        """Send recent messages to user"""
        try:
            chat_service = ChatService()
            messages = await database_sync_to_async(chat_service.get_messages)(
                room, self.user, 20
            )
            
            for message in messages:
                await self.send(text_data=json.dumps({
                    'type': 'support_message',
                    'message': {
                        'id': str(message.id),
                        'sender_id': message.sender.id,
                        'sender_username': chat_user_display_name(message.sender),
                        'content': message.content,
                        'message_type': message.message_type,
                        'sent_at': message.sent_at.isoformat(),
                        'status': message.status,
                    }
                }))
        except Exception as e:
            logger.error(f"Error sending recent messages: {e}")
