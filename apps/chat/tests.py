"""
Comprehensive Tests for Chat and Support System
Unit and integration tests for chat rooms, messages, and support tickets
"""

from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.exceptions import ValidationError
from django.utils import timezone
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.urls import reverse
from asgiref.sync import async_to_sync
from channels.testing import WebsocketCommunicator
from unittest.mock import patch, MagicMock
import json
import uuid

from .models import (
    ChatRoom, ChatParticipant, ChatMessage, ChatMessageRead,
    SupportTicket, ChatAnalytics
)
from .services import (
    ChatService, ChatMembershipError, SupportService, ChatAnalyticsService,
)
from config.asgi import application

User = get_user_model()


class ChatModelTests(TestCase):
    """Test cases for chat models"""
    
    def setUp(self):
        """Set up test data"""
        self.user1 = User.objects.create_user(
            mobile_number='09123456789',
            email='user1@test.com',
            password='testpass123'
        )
        self.user2 = User.objects.create_user(
            mobile_number='09123456790',
            email='user2@test.com',
            password='testpass123'
        )
        self.user3 = User.objects.create_user(
            mobile_number='09123456791',
            email='user3@test.com',
            password='testpass123'
        )
    
    def test_chat_room_creation(self):
        """Test chat room creation"""
        room = ChatRoom.objects.create(
            name='Test Room',
            description='Test Description',
            room_type=ChatRoom.PRIVATE,
            created_by=self.user1
        )
        
        self.assertEqual(room.name, 'Test Room')
        self.assertEqual(room.room_type, ChatRoom.PRIVATE)
        self.assertEqual(room.created_by, self.user1)
        self.assertEqual(room.status, ChatRoom.ACTIVE)
        self.assertFalse(room.is_encrypted)
        self.assertTrue(room.allow_file_sharing)
        self.assertEqual(room.max_participants, 100)
    
    def test_chat_room_participant_management(self):
        """Test chat room participant management"""
        room = ChatRoom.objects.create(
            name='Test Room',
            created_by=self.user1
        )
        
        # Add participants (including creator)
        room.add_participant(self.user1, 'admin')  # creator
        room.add_participant(self.user2, 'member')
        room.add_participant(self.user3, 'moderator')
        
        # Check participant count
        self.assertEqual(room.get_participant_count(), 3)  # creator + 2 participants
        
        # Check if users are participants
        self.assertTrue(room.is_participant(self.user1))
        self.assertTrue(room.is_participant(self.user2))
        self.assertTrue(room.is_participant(self.user3))
        
        # Remove participant
        room.remove_participant(self.user2)
        self.assertEqual(room.get_participant_count(), 2)
        self.assertFalse(room.is_participant(self.user2))
    
    def test_chat_message_creation(self):
        """Test chat message creation"""
        room = ChatRoom.objects.create(
            name='Test Room',
            created_by=self.user1
        )
        
        message = ChatMessage.objects.create(
            chat_room=room,
            sender=self.user1,
            content='Hello, world!',
            message_type=ChatMessage.TEXT
        )
        
        self.assertEqual(message.content, 'Hello, world!')
        self.assertEqual(message.message_type, ChatMessage.TEXT)
        self.assertEqual(message.status, ChatMessage.SENT)
        self.assertFalse(message.is_edited)
        self.assertFalse(message.is_deleted)
    
    def test_chat_message_status_updates(self):
        """Test chat message status updates"""
        room = ChatRoom.objects.create(
            name='Test Room',
            created_by=self.user1
        )
        
        message = ChatMessage.objects.create(
            chat_room=room,
            sender=self.user1,
            content='Test message'
        )
        
        # Mark as delivered
        message.mark_as_delivered()
        self.assertEqual(message.status, ChatMessage.DELIVERED)
        self.assertIsNotNone(message.delivered_at)
        
        # Mark as read
        message.mark_as_read()
        self.assertEqual(message.status, ChatMessage.READ)
        self.assertIsNotNone(message.read_at)
    
    def test_chat_message_editing(self):
        """Test chat message editing"""
        room = ChatRoom.objects.create(
            name='Test Room',
            created_by=self.user1
        )
        
        message = ChatMessage.objects.create(
            chat_room=room,
            sender=self.user1,
            content='Original content'
        )
        
        # Edit message
        message.edit_message('Edited content')
        
        self.assertEqual(message.content, 'Edited content')
        self.assertTrue(message.is_edited)
        self.assertIsNotNone(message.edited_at)
    
    def test_support_ticket_creation(self):
        """Test support ticket creation"""
        # Create a chat room first
        room = ChatRoom.objects.create(
            name='Support Chat',
            room_type=ChatRoom.SUPPORT,
            created_by=self.user1
        )
        
        ticket = SupportTicket.objects.create(
            user=self.user1,
            subject='Test Ticket',
            description='Test Description',
            category=SupportTicket.TECHNICAL,
            priority=SupportTicket.HIGH,
            chat_room=room
        )
        
        self.assertEqual(ticket.subject, 'Test Ticket')
        self.assertEqual(ticket.category, SupportTicket.TECHNICAL)
        self.assertEqual(ticket.priority, SupportTicket.HIGH)
        self.assertEqual(ticket.status, SupportTicket.OPEN)
        self.assertIsNotNone(ticket.ticket_number)
        self.assertIsNotNone(ticket.chat_room)
    
    def test_support_ticket_status_updates(self):
        """Test support ticket status updates"""
        # Create a chat room first
        room = ChatRoom.objects.create(
            name='Support Chat',
            room_type=ChatRoom.SUPPORT,
            created_by=self.user1
        )
        
        ticket = SupportTicket.objects.create(
            user=self.user1,
            subject='Test Ticket',
            description='Test Description',
            chat_room=room
        )
        
        # Assign ticket
        ticket.assign_to(self.user2)
        self.assertEqual(ticket.assigned_to, self.user2)
        self.assertEqual(ticket.status, SupportTicket.IN_PROGRESS)
        
        # Resolve ticket
        ticket.resolve('Test resolution')
        self.assertEqual(ticket.status, SupportTicket.RESOLVED)
        self.assertEqual(ticket.resolution, 'Test resolution')
        self.assertIsNotNone(ticket.resolved_at)
        
        # Close ticket
        ticket.close()
        self.assertEqual(ticket.status, SupportTicket.CLOSED)
        self.assertIsNotNone(ticket.closed_at)


class ChatServiceTests(TestCase):
    """Test cases for chat services"""
    
    def setUp(self):
        """Set up test data"""
        self.user1 = User.objects.create_user(
            mobile_number='09123456789',
            email='user1@test.com',
            password='testpass123'
        )
        self.user2 = User.objects.create_user(
            mobile_number='09123456790',
            email='user2@test.com',
            password='testpass123'
        )
        self.chat_service = ChatService()
    
    def test_create_chat_room(self):
        """Test creating chat room with service"""
        room = self.chat_service.create_chat_room(
            name='Test Room',
            room_type=ChatRoom.PRIVATE,
            description='Test Description',
            created_by=self.user1,
            participants=[self.user2]
        )
        
        self.assertEqual(room.name, 'Test Room')
        self.assertEqual(room.room_type, ChatRoom.PRIVATE)
        self.assertEqual(room.created_by, self.user1)
        self.assertTrue(room.is_participant(self.user1))
        self.assertTrue(room.is_participant(self.user2))
    
    def test_send_message(self):
        """Test sending message with service"""
        room = self.chat_service.create_chat_room(
            name='Test Room',
            created_by=self.user1,
            participants=[self.user2]
        )
        
        message = self.chat_service.send_message(
            chat_room=room,
            sender=self.user1,
            content='Hello, world!',
            message_type=ChatMessage.TEXT
        )
        
        self.assertEqual(message.content, 'Hello, world!')
        self.assertEqual(message.sender, self.user1)
        self.assertEqual(message.chat_room, room)
        self.assertEqual(message.message_type, ChatMessage.TEXT)
    
    def test_get_messages(self):
        """Test getting messages with service"""
        room = self.chat_service.create_chat_room(
            name='Test Room',
            created_by=self.user1,
            participants=[self.user2]
        )
        
        # Send multiple messages
        for i in range(5):
            self.chat_service.send_message(
                chat_room=room,
                sender=self.user1,
                content=f'Message {i}'
            )
        
        # Get messages
        messages = self.chat_service.get_messages(room, self.user1, limit=10)
        
        self.assertEqual(len(messages), 5)
        self.assertEqual(messages[0].content, 'Message 4')  # Most recent first
    
    def test_mark_message_as_read(self):
        """Test marking message as read with service"""
        room = self.chat_service.create_chat_room(
            name='Test Room',
            created_by=self.user1,
            participants=[self.user2]
        )
        
        message = self.chat_service.send_message(
            chat_room=room,
            sender=self.user1,
            content='Test message'
        )
        
        # Mark as read
        success = self.chat_service.mark_message_as_read(message, self.user2)
        
        self.assertTrue(success)
        self.assertEqual(message.status, ChatMessage.READ)
    
    def test_get_unread_count(self):
        """Test getting unread count with service"""
        room = self.chat_service.create_chat_room(
            name='Test Room',
            created_by=self.user1,
            participants=[self.user2]
        )
        
        # Send messages
        for i in range(3):
            self.chat_service.send_message(
                chat_room=room,
                sender=self.user1,
                content=f'Message {i}'
            )
        
        # Get unread count for user2
        unread_count = self.chat_service.get_unread_count(room, self.user2)
        
        self.assertEqual(unread_count, 3)


class SupportServiceTests(TestCase):
    """Test cases for support services"""
    
    def setUp(self):
        """Set up test data"""
        self.user1 = User.objects.create_user(
            mobile_number='09123456789',
            email='user1@test.com',
            password='testpass123'
        )
        self.agent = User.objects.create_user(
            mobile_number='09123456790',
            email='agent@test.com',
            password='testpass123',
            is_staff=True
        )
        self.support_service = SupportService()
    
    def test_create_support_ticket(self):
        """Test creating support ticket with service"""
        ticket = self.support_service.create_support_ticket(
            user=self.user1,
            subject='Test Ticket',
            description='Test Description',
            category=SupportTicket.TECHNICAL,
            priority=SupportTicket.HIGH
        )
        
        self.assertEqual(ticket.subject, 'Test Ticket')
        self.assertEqual(ticket.user, self.user1)
        self.assertEqual(ticket.category, SupportTicket.TECHNICAL)
        self.assertEqual(ticket.priority, SupportTicket.HIGH)
        self.assertIsNotNone(ticket.chat_room)
    
    def test_assign_ticket(self):
        """Test assigning ticket with service"""
        ticket = self.support_service.create_support_ticket(
            user=self.user1,
            subject='Test Ticket',
            description='Test Description'
        )
        
        success = self.support_service.assign_ticket(
            ticket, self.agent, self.agent
        )
        
        self.assertTrue(success)
        self.assertEqual(ticket.assigned_to, self.agent)
        self.assertEqual(ticket.status, SupportTicket.IN_PROGRESS)
    
    def test_resolve_ticket(self):
        """Test resolving ticket with service"""
        ticket = self.support_service.create_support_ticket(
            user=self.user1,
            subject='Test Ticket',
            description='Test Description'
        )
        
        ticket.assign_to(self.agent)
        
        success = self.support_service.resolve_ticket(
            ticket, 'Test resolution', self.agent
        )
        
        self.assertTrue(success)
        self.assertEqual(ticket.status, SupportTicket.RESOLVED)
        self.assertEqual(ticket.resolution, 'Test resolution')
    
    def test_get_ticket_stats(self):
        """Test getting ticket statistics with service"""
        # Create multiple tickets
        for i in range(3):
            self.support_service.create_support_ticket(
                user=self.user1,
                subject=f'Ticket {i}',
                description=f'Description {i}'
            )
        
        stats = self.support_service.get_ticket_stats(self.user1)
        
        self.assertEqual(stats['total_tickets'], 3)
        self.assertEqual(stats['open_tickets'], 3)


class ChatAPITests(APITestCase):
    """Test cases for chat API endpoints"""
    
    def setUp(self):
        """Set up test data"""
        self.user1 = User.objects.create_user(
            mobile_number='09123456789',
            email='user1@test.com',
            password='testpass123'
        )
        self.user2 = User.objects.create_user(
            mobile_number='09123456790',
            email='user2@test.com',
            password='testpass123'
        )
        self.client = APIClient()
    
    def test_create_chat_room_api(self):
        """Test creating chat room via API"""
        self.client.force_authenticate(user=self.user1)
        
        data = {
            'name': 'Test Room',
            'description': 'Test Description',
            'room_type': ChatRoom.PRIVATE,
            'participants': [self.user2.id]
        }
        
        response = self.client.post('/api/v1/chat/rooms/', data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['id'], str(ChatRoom.objects.get().id))
        self.assertEqual(ChatRoom.objects.count(), 1)
        
        room = ChatRoom.objects.first()
        self.assertEqual(room.name, 'Test Room')
        self.assertTrue(room.is_participant(self.user1))
        self.assertTrue(room.is_participant(self.user2))
    
    def test_send_message_api(self):
        """Test sending message via API"""
        self.client.force_authenticate(user=self.user1)
        
        # Create room
        room = ChatRoom.objects.create(
            name='Test Room',
            created_by=self.user1
        )
        room.add_participant(self.user1)
        room.add_participant(self.user2)
        
        data = {
            'chat_room_id': str(room.id),
            'content': 'Hello, world!',
            'message_type': ChatMessage.TEXT
        }
        
        response = self.client.post('/api/v1/chat/messages/', data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['id'], str(ChatMessage.objects.get().id))
        self.assertEqual(ChatMessage.objects.count(), 1)
        
        message = ChatMessage.objects.first()
        self.assertEqual(message.content, 'Hello, world!')
        self.assertEqual(message.sender, self.user1)
    
    def test_get_room_messages_api(self):
        """Test getting room messages via API"""
        self.client.force_authenticate(user=self.user1)
        
        # Create room and messages
        room = ChatRoom.objects.create(
            name='Test Room',
            created_by=self.user1
        )
        room.add_participant(self.user1)
        room.add_participant(self.user2)
        
        for i in range(3):
            ChatMessage.objects.create(
                chat_room=room,
                sender=self.user1,
                content=f'Message {i}'
            )
        
        response = self.client.get(f'/api/v1/chat/messages/room_messages/?room_id={room.id}')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 3)
    
    def test_create_support_ticket_api(self):
        """Test creating support ticket via API"""
        self.client.force_authenticate(user=self.user1)
        
        data = {
            'subject': 'Test Ticket',
            'description': 'Test Description',
            'category': SupportTicket.TECHNICAL,
            'priority': SupportTicket.HIGH
        }
        
        response = self.client.post('/api/v1/chat/support/tickets/', data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(SupportTicket.objects.count(), 1)
        self.assertEqual(ChatRoom.objects.count(), 1)
        
        ticket = SupportTicket.objects.first()
        self.assertEqual(ticket.subject, 'Test Ticket')
        self.assertEqual(ticket.user, self.user1)
    
    def test_assign_ticket_api(self):
        """Test assigning ticket via API"""
        self.client.force_authenticate(user=self.user1)
        
        # Create a chat room first
        room = ChatRoom.objects.create(
            name='Support Chat',
            room_type=ChatRoom.SUPPORT,
            created_by=self.user1
        )
        
        # Create ticket
        ticket = SupportTicket.objects.create(
            user=self.user1,
            subject='Test Ticket',
            description='Test Description',
            chat_room=room
        )
        
        # Create staff user
        staff_user = User.objects.create_user(
            mobile_number='09123456791',
            email='staff@test.com',
            password='testpass123',
            is_staff=True
        )
        
        self.client.force_authenticate(user=staff_user)
        
        data = {'agent_id': staff_user.id}
        response = self.client.post(f'/api/v1/chat/support/tickets/{ticket.id}/assign/', data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        ticket.refresh_from_db()
        self.assertEqual(ticket.assigned_to, staff_user)
        self.assertEqual(ticket.status, SupportTicket.IN_PROGRESS)
    
    def test_unauthorized_access(self):
        """Test unauthorized access to API"""
        # Test without authentication
        response = self.client.get('/api/v1/chat/rooms/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        
        # Test with authentication but no access
        self.client.force_authenticate(user=self.user1)
        
        room = ChatRoom.objects.create(
            name='Private Room',
            created_by=self.user2
        )
        
        response = self.client.get(f'/api/v1/chat/messages/room_messages/?room_id={room.id}')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class ChatWebSocketTests(TransactionTestCase):
    """Test cases for WebSocket functionality"""
    
    def setUp(self):
        """Set up test data"""
        self.user1 = User.objects.create_user(
            mobile_number='09123456789',
            email='user1@test.com',
            password='testpass123'
        )
        self.user2 = User.objects.create_user(
            mobile_number='09123456790',
            email='user2@test.com',
            password='testpass123'
        )
        self.room = ChatService().create_chat_room(
            name='Socket room',
            created_by=self.user1,
            participants=[self.user2],
        )
    
    def test_websocket_connection(self):
        """A room participant authenticates with a path-bound ticket."""
        async def scenario():
            payload = {'user_id': str(self.user1.pk), 'scope': 'chat'}
            with patch(
                'apps.core.ws_auth.WebSocketTicketStore.consume',
                return_value=payload,
            ):
                communicator = WebsocketCommunicator(
                    application,
                    f'/ws/chat/{self.room.id}/?ticket=test-ticket',
                    headers=[(b'host', b'localhost'), (b'origin', b'http://localhost')],
                )
                connected, _ = await communicator.connect()
                self.assertTrue(connected)
                frame = await communicator.receive_json_from(timeout=2)
                self.assertEqual(frame['type'], 'connection_established')
                await communicator.disconnect()

        async_to_sync(scenario)()
    
    def test_websocket_message_handling(self):
        """A socket message is persisted and echoed without removed user fields."""
        async def scenario():
            payload = {'user_id': str(self.user1.pk), 'scope': 'chat'}
            with patch(
                'apps.core.ws_auth.WebSocketTicketStore.consume',
                return_value=payload,
            ):
                communicator = WebsocketCommunicator(
                    application,
                    f'/ws/chat/{self.room.id}/?ticket=test-ticket',
                    headers=[(b'host', b'localhost'), (b'origin', b'http://localhost')],
                )
                connected, _ = await communicator.connect()
                self.assertTrue(connected)
                await communicator.receive_json_from(timeout=2)
                await communicator.send_json_to({
                    'type': 'chat_message',
                    'content': 'Socket message',
                    'message_type': 'text',
                })

                message_frame = None
                for _ in range(3):
                    frame = await communicator.receive_json_from(timeout=2)
                    if frame.get('type') == 'chat_message':
                        message_frame = frame
                        break

                self.assertIsNotNone(message_frame)
                self.assertEqual(message_frame['message']['content'], 'Socket message')
                self.assertTrue(message_frame['message']['sender_username'])
                await communicator.disconnect()

        async_to_sync(scenario)()
        self.assertTrue(
            ChatMessage.objects.filter(
                chat_room=self.room,
                sender=self.user1,
                content='Socket message',
            ).exists()
        )


class ChatIntegrationTests(TestCase):
    """Integration tests for chat system"""
    
    def setUp(self):
        """Set up test data"""
        self.user1 = User.objects.create_user(
            mobile_number='09123456789',
            email='user1@test.com',
            password='testpass123'
        )
        self.user2 = User.objects.create_user(
            mobile_number='09123456790',
            email='user2@test.com',
            password='testpass123'
        )
        self.chat_service = ChatService()
        self.support_service = SupportService()
    
    def test_complete_chat_flow(self):
        """Test complete chat flow from room creation to message exchange"""
        # Create room
        room = self.chat_service.create_chat_room(
            name='Test Room',
            created_by=self.user1,
            participants=[self.user2]
        )
        
        # Send messages
        message1 = self.chat_service.send_message(
            chat_room=room,
            sender=self.user1,
            content='Hello!'
        )
        
        message2 = self.chat_service.send_message(
            chat_room=room,
            sender=self.user2,
            content='Hi there!'
        )
        
        # Mark messages as read
        self.chat_service.mark_message_as_read(message1, self.user2)
        self.chat_service.mark_message_as_read(message2, self.user1)
        
        # Verify final state
        self.assertEqual(ChatRoom.objects.count(), 1)
        self.assertEqual(ChatMessage.objects.count(), 2)
        self.assertEqual(ChatMessageRead.objects.count(), 2)
        
        # Chat analytics are updated from the real message rows.
        analytics = ChatAnalytics.objects.get(chat_room=room)
        self.assertEqual(analytics.total_messages, 2)
        self.assertEqual(analytics.active_participants, 2)
    
    def test_support_ticket_flow(self):
        """Test complete support ticket flow"""
        # Create ticket
        ticket = self.support_service.create_support_ticket(
            user=self.user1,
            subject='Test Issue',
            description='I need help with something'
        )
        
        # Assign ticket
        agent = User.objects.create_user(
            mobile_number='09123456792',
            email='agent@test.com',
            password='testpass123',
            is_staff=True
        )
        
        self.support_service.assign_ticket(ticket, agent, agent)
        
        # Send messages in support chat
        room = ticket.chat_room
        self.chat_service.send_message(
            chat_room=room,
            sender=self.user1,
            content='I need help with my account'
        )
        
        self.chat_service.send_message(
            chat_room=room,
            sender=agent,
            content='I can help you with that. What seems to be the issue?'
        )
        
        # Resolve ticket
        self.support_service.resolve_ticket(
            ticket, 'Issue resolved successfully', agent
        )
        
        # Verify final state
        self.assertEqual(SupportTicket.objects.count(), 1)
        self.assertEqual(ticket.status, SupportTicket.RESOLVED)
        self.assertEqual(ChatMessage.objects.count(), 2)
    
    def test_file_upload_flow(self):
        """Test file upload flow"""
        room = self.chat_service.create_chat_room(
            name='Test Room',
            created_by=self.user1,
            participants=[self.user2]
        )
        
        # Create test file
        test_file = SimpleUploadedFile(
            'test.txt',
            b'Test file content',
            content_type='text/plain'
        )
        
        # Send message with file
        message = self.chat_service.send_message(
            chat_room=room,
            sender=self.user1,
            content='Here is a test file',
            message_type=ChatMessage.FILE,
            file=test_file
        )
        
        # Verify file attachment
        self.assertEqual(message.message_type, ChatMessage.FILE)
        self.assertIsNotNone(message.file)
        self.assertEqual(message.file_name, 'test.txt')
        self.assertEqual(message.file_size, 17)  # Length of 'Test file content'
        self.assertEqual(message.file_type, 'text/plain')
    
    def test_room_permissions(self):
        """Test room permissions and access control"""
        room = self.chat_service.create_chat_room(
            name='Test Room',
            created_by=self.user1,
            participants=[self.user2]
        )
        
        # Test participant access
        self.assertTrue(room.is_participant(self.user1))
        self.assertTrue(room.is_participant(self.user2))
        
        # Test non-participant access
        user3 = User.objects.create_user(
            mobile_number='09123456793',
            email='user3@test.com',
            password='testpass123'
        )
        self.assertFalse(room.is_participant(user3))
        
        # Direct-chat membership remains system-managed.
        with self.assertRaises(ChatMembershipError):
            self.chat_service.add_participant(room, user3, self.user1)

        group = self.chat_service.create_chat_room(
            name='Managed group',
            room_type=ChatRoom.GROUP,
            created_by=self.user1,
            participants=[self.user2],
        )
        self.chat_service.add_participant(group, user3, self.user1)
        self.assertTrue(group.is_participant(user3))
        self.chat_service.remove_participant(group, user3, user3)
        self.assertFalse(group.is_participant(user3))
    
    def test_message_search(self):
        """Test message search functionality"""
        room = self.chat_service.create_chat_room(
            name='Test Room',
            created_by=self.user1,
            participants=[self.user2]
        )
        
        # Send messages with different content
        messages = [
            'Hello world',
            'This is a test message',
            'Another message with test content',
            'Final message'
        ]
        
        for content in messages:
            self.chat_service.send_message(
                chat_room=room,
                sender=self.user1,
                content=content
            )
        
        # Test search
        from django.db.models import Q
        search_results = ChatMessage.objects.filter(
            chat_room=room,
            content__icontains='test'
        )
        
        self.assertEqual(search_results.count(), 2)
        self.assertIn('This is a test message', [msg.content for msg in search_results])
        self.assertIn('Another message with test content', [msg.content for msg in search_results])
