"""
Advanced Chat and Support Services for ASOUD Platform
Comprehensive chat system with real-time messaging, file sharing, and support tickets
"""

import logging
import time
import os
import mimetypes
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from django.conf import settings
from django.utils import timezone
from django.core.cache import cache
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q, Count, Avg, Max
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from .models import (
    ChatRoom, ChatParticipant, ChatMembershipEvent, ChatMessage, ChatMessageRead,
    SupportTicket, ChatAnalytics
)

User = get_user_model()
logger = logging.getLogger(__name__)


class ChatMembershipError(Exception):
    """Stable service-layer error consumed by REST and other transports."""

    def __init__(self, code, message, http_status=400):
        self.code = code
        self.message = message
        self.http_status = http_status
        super().__init__(message)


class ChatService:
    """
    Main chat service for handling all chat operations
    """
    
    def __init__(self):
        self.max_file_size = getattr(settings, 'CHAT_MAX_FILE_SIZE', 10 * 1024 * 1024)  # 10MB
        self.allowed_file_types = getattr(settings, 'CHAT_ALLOWED_FILE_TYPES', [
            'image/jpeg', 'image/png', 'image/gif', 'image/webp',
            'application/pdf', 'text/plain', 'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'audio/mpeg', 'audio/wav', 'video/mp4', 'video/avi'
        ])
    
    def create_chat_room(
        self,
        name: str,
        room_type: str = ChatRoom.PRIVATE,
        description: str = '',
        created_by: User = None,
        participants: List[User] = None,
        content_object=None,
        **kwargs
    ) -> ChatRoom:
        """
        Create a new chat room
        
        Args:
            name: Room name
            room_type: Type of room (private, group, support, market)
            description: Room description
            created_by: User who created the room
            participants: List of participants
            content_object: Related object (e.g., Market, Order)
            **kwargs: Additional room settings
            
        Returns:
            ChatRoom: Created chat room
        """
        try:
            with transaction.atomic():
                platform_cap = getattr(settings, 'CHAT_GROUP_MAX_PARTICIPANTS', 100)
                requested_limit = kwargs.pop('max_participants', 100)
                if room_type == ChatRoom.GROUP:
                    if requested_limit < 2 or requested_limit > platform_cap:
                        raise ChatMembershipError(
                            'invalid_participant_limit',
                            f'Group capacity must be between 2 and {platform_cap}.',
                        )
                    unique_participants = {
                        participant.pk: participant for participant in (participants or [])
                        if participant != created_by
                    }
                    if len(unique_participants) + (1 if created_by else 0) > requested_limit:
                        raise ChatMembershipError(
                            'participant_limit_reached',
                            'Initial participants exceed the room capacity.',
                            409,
                        )
                    participants = list(unique_participants.values())
                else:
                    requested_limit = 2 if room_type == ChatRoom.PRIVATE else requested_limit

                # Create chat room
                chat_room = ChatRoom.objects.create(
                    name=name,
                    room_type=room_type,
                    description=description,
                    created_by=created_by,
                    content_object=content_object,
                    max_participants=requested_limit,
                    **kwargs
                )

                if created_by:
                    creator_role = (
                        ChatParticipant.OWNER
                        if room_type == ChatRoom.GROUP
                        else ChatParticipant.MEMBER
                    )
                    ChatParticipant.objects.create(
                        chat_room=chat_room,
                        user=created_by,
                        role=creator_role,
                    )
                    if room_type == ChatRoom.GROUP:
                        self._audit_membership(
                            chat_room,
                            created_by,
                            created_by,
                            ChatMembershipEvent.MEMBER_ADDED,
                            new_role=creator_role,
                        )
                
                # Add participants
                if participants:
                    for participant in participants:
                        if participant != created_by:  # Don't add creator twice
                            membership, created = ChatParticipant.objects.get_or_create(
                                chat_room=chat_room,
                                user=participant,
                                defaults={
                                    'role': ChatParticipant.MEMBER,
                                    'invited_by': created_by,
                                },
                            )
                            if created and room_type == ChatRoom.GROUP:
                                self._audit_membership(
                                    chat_room,
                                    created_by,
                                    participant,
                                    ChatMembershipEvent.MEMBER_ADDED,
                                    new_role=membership.role,
                                )
                
                # Initialize analytics
                ChatAnalytics.objects.create(chat_room=chat_room)
                
                logger.info(f"Created chat room {chat_room.id} of type {room_type}")
                return chat_room
                
        except Exception as e:
            logger.error(f"Error creating chat room: {e}")
            raise
    
    def send_message(
        self,
        chat_room: ChatRoom,
        sender: User,
        content: str,
        message_type: str = ChatMessage.TEXT,
        file=None,
        reply_to: ChatMessage = None,
        **kwargs
    ) -> ChatMessage:
        """
        Send a message to a chat room
        
        Args:
            chat_room: Target chat room
            sender: Message sender
            content: Message content
            message_type: Type of message (text, image, file, etc.)
            file: File attachment
            reply_to: Message being replied to
            **kwargs: Additional message data
            
        Returns:
            ChatMessage: Created message
        """
        try:
            # Check if user is participant
            if not chat_room.is_participant(sender):
                raise ValidationError("User is not a participant in this chat room")
            
            # Validate file if provided
            file_data = None
            if file and message_type in [ChatMessage.IMAGE, ChatMessage.FILE, ChatMessage.AUDIO, ChatMessage.VIDEO]:
                file_data = self._validate_and_process_file(file)
            
            with transaction.atomic():
                # Create message
                message = ChatMessage.objects.create(
                    chat_room=chat_room,
                    sender=sender,
                    content=content,
                    message_type=message_type,
                    reply_to=reply_to,
                    file=file_data['file'] if file_data else None,
                    file_name=file_data['file_name'] if file_data else None,
                    file_size=file_data['file_size'] if file_data else None,
                    file_type=file_data['file_type'] if file_data else None,
                    **kwargs
                )
                
                # Update room last message time
                chat_room.last_message_at = timezone.now()
                chat_room.update_last_activity()
                chat_room.save(update_fields=['last_message_at', 'last_activity_at'])
                
                # Update analytics
                self._update_message_analytics(chat_room)
                
                logger.info(f"Message {message.id} sent to room {chat_room.id}")
                return message
                
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            raise
    
    def get_messages(
        self,
        chat_room: ChatRoom,
        user: User,
        limit: int = 50,
        offset: int = 0,
        message_type: str = None
    ) -> List[ChatMessage]:
        """
        Get messages from a chat room
        
        Args:
            chat_room: Target chat room
            user: Requesting user
            limit: Number of messages to return
            offset: Number of messages to skip
            message_type: Filter by message type
            
        Returns:
            List[ChatMessage]: List of messages
        """
        try:
            # Check if user is participant
            if not chat_room.is_participant(user):
                raise ValidationError("User is not a participant in this chat room")
            
            # Build query
            query = Q(chat_room=chat_room, is_deleted=False)
            
            if message_type:
                query &= Q(message_type=message_type)
            
            # Get messages
            messages = ChatMessage.objects.filter(query).select_related(
                'sender', 'reply_to', 'reply_to__sender'
            ).order_by('-sent_at')[offset:offset + limit]
            
            # Mark messages as delivered for this user
            self._mark_messages_as_delivered(messages, user)
            
            return list(messages)
            
        except Exception as e:
            logger.error(f"Error getting messages: {e}")
            raise
    
    def mark_message_as_read(self, message: ChatMessage, user: User) -> bool:
        """
        Mark a message as read by a user
        
        Args:
            message: Message to mark as read
            user: User who read the message
            
        Returns:
            bool: Success status
        """
        try:
            # Check if user is participant
            if not message.chat_room.is_participant(user):
                return False
            
            # Create or update read record
            ChatMessageRead.objects.update_or_create(
                message=message,
                user=user,
                defaults={'read_at': timezone.now()}
            )
            
            # Update message status if all participants have read it
            self._update_message_read_status(message)
            
            logger.info("Message %s marked as read by user %s", message.id, user.pk)
            return True
            
        except Exception as e:
            logger.error(f"Error marking message as read: {e}")
            return False
    
    def get_unread_count(self, chat_room: ChatRoom, user: User) -> int:
        """
        Get unread message count for a user in a chat room
        
        Args:
            chat_room: Target chat room
            user: User to check
            
        Returns:
            int: Number of unread messages
        """
        try:
            if not chat_room.is_participant(user):
                return 0

            # Read state is represented by ChatMessageRead. Participant timestamp
            # fields no longer exist in the current schema.
            return ChatMessage.objects.filter(
                chat_room=chat_room,
                is_deleted=False
            ).exclude(sender=user).exclude(read_by__user=user).count()
            
        except Exception as e:
            logger.error(f"Error getting unread count: {e}")
            return 0
    
    def add_participant(
        self,
        chat_room: ChatRoom,
        user: User,
        added_by: User,
    ) -> bool:
        """
        Add a participant to a chat room
        
        Args:
            chat_room: Target chat room
            user: User to add
            added_by: User who is adding
        Returns:
            bool: Success status
        """
        return self.add_group_participant(chat_room, user, added_by)
    
    def remove_participant(
        self,
        chat_room: ChatRoom,
        user: User,
        removed_by: User
    ) -> bool:
        """
        Remove a participant from a chat room
        
        Args:
            chat_room: Target chat room
            user: User to remove
            removed_by: User who is removing
            
        Returns:
            bool: Success status
        """
        if removed_by == user:
            self.leave_group(chat_room, user)
            return True
        self.remove_group_participant(chat_room, user, removed_by)
        return True

    @staticmethod
    def _require_group(room):
        if room.room_type != ChatRoom.GROUP:
            raise ChatMembershipError(
                'membership_system_managed',
                'Membership for this room type is system-managed.',
                409,
            )
        if room.status != ChatRoom.ACTIVE:
            raise ChatMembershipError('room_not_active', 'The room is not active.', 409)

    @staticmethod
    def _membership(room, user):
        try:
            return ChatParticipant.objects.get(chat_room=room, user=user)
        except ChatParticipant.DoesNotExist as exc:
            raise ChatMembershipError('not_a_participant', 'User is not a room participant.', 403) from exc

    @staticmethod
    def _audit_membership(room, actor, subject, action, old_role=None, new_role=None):
        ChatMembershipEvent.objects.create(
            chat_room=room,
            actor=actor,
            subject=subject,
            action=action,
            old_role=old_role,
            new_role=new_role,
        )

    @staticmethod
    def _notify_membership(room, event_type, user, role=None):
        def publish():
            channel_layer = get_channel_layer()
            if channel_layer is None:
                return
            async_to_sync(channel_layer.group_send)(
                f'chat_{room.id}',
                {
                    'type': event_type,
                    'user_id': user.pk,
                    'role': role,
                },
            )

        transaction.on_commit(publish)

    def add_group_participant(self, chat_room, user, added_by, role=ChatParticipant.MEMBER):
        if role not in (ChatParticipant.ADMIN, ChatParticipant.MEMBER):
            raise ChatMembershipError('invalid_role', 'Only admin or member may be assigned.', 400)
        with transaction.atomic():
            room = ChatRoom.objects.select_for_update().get(pk=chat_room.pk)
            self._require_group(room)
            actor_membership = self._membership(room, added_by)
            if actor_membership.role not in (ChatParticipant.OWNER, ChatParticipant.ADMIN):
                raise ChatMembershipError('permission_denied', 'You cannot add participants.', 403)
            if actor_membership.role == ChatParticipant.ADMIN and role != ChatParticipant.MEMBER:
                raise ChatMembershipError('permission_denied', 'Admins may add members only.', 403)
            if ChatParticipant.objects.filter(chat_room=room, user=user).exists():
                raise ChatMembershipError(
                    'participant_already_member',
                    'The user is already a participant.',
                    409,
                )
            platform_cap = getattr(settings, 'CHAT_GROUP_MAX_PARTICIPANTS', 100)
            effective_limit = min(room.max_participants, platform_cap)
            if ChatParticipant.objects.filter(chat_room=room).count() >= effective_limit:
                raise ChatMembershipError(
                    'participant_limit_reached',
                    f'This room has reached its {effective_limit}-participant limit.',
                    409,
                )
            membership = ChatParticipant.objects.create(
                chat_room=room,
                user=user,
                role=role,
                invited_by=added_by,
            )
            self._audit_membership(
                room,
                added_by,
                user,
                ChatMembershipEvent.MEMBER_ADDED,
                new_role=role,
            )
            self._notify_membership(room, 'membership_updated', user, role)
            return membership

    def remove_group_participant(self, chat_room, user, removed_by):
        with transaction.atomic():
            room = ChatRoom.objects.select_for_update().get(pk=chat_room.pk)
            self._require_group(room)
            actor_membership = self._membership(room, removed_by)
            target = self._membership(room, user)
            if target.role == ChatParticipant.OWNER:
                raise ChatMembershipError(
                    'ownership_transfer_required',
                    'Transfer ownership before removing the owner.',
                    409,
                )
            allowed = actor_membership.role == ChatParticipant.OWNER or (
                actor_membership.role == ChatParticipant.ADMIN
                and target.role == ChatParticipant.MEMBER
            )
            if not allowed:
                raise ChatMembershipError('permission_denied', 'You cannot remove this participant.', 403)
            old_role = target.role
            target.delete()
            self._audit_membership(
                room,
                removed_by,
                user,
                ChatMembershipEvent.MEMBER_REMOVED,
                old_role=old_role,
            )
            self._notify_membership(room, 'membership_revoked', user)

    def change_group_role(self, chat_room, user, changed_by, role):
        if role not in (ChatParticipant.ADMIN, ChatParticipant.MEMBER):
            raise ChatMembershipError('invalid_role', 'Only admin or member may be assigned.', 400)
        with transaction.atomic():
            room = ChatRoom.objects.select_for_update().get(pk=chat_room.pk)
            self._require_group(room)
            actor_membership = self._membership(room, changed_by)
            target = self._membership(room, user)
            if actor_membership.role != ChatParticipant.OWNER:
                raise ChatMembershipError('permission_denied', 'Only the owner may change roles.', 403)
            if target.role == ChatParticipant.OWNER:
                raise ChatMembershipError(
                    'ownership_transfer_required',
                    'Use the ownership transfer endpoint.',
                    409,
                )
            if target.role == role:
                return target
            old_role = target.role
            target.role = role
            target.role_updated_at = timezone.now()
            target.save(update_fields=['role', 'role_updated_at'])
            self._audit_membership(
                room,
                changed_by,
                user,
                ChatMembershipEvent.ROLE_CHANGED,
                old_role=old_role,
                new_role=role,
            )
            self._notify_membership(room, 'membership_updated', user, role)
            return target

    def transfer_group_ownership(self, chat_room, target_user, owner):
        with transaction.atomic():
            room = ChatRoom.objects.select_for_update().get(pk=chat_room.pk)
            self._require_group(room)
            current_owner = self._membership(room, owner)
            target = self._membership(room, target_user)
            if current_owner.role != ChatParticipant.OWNER:
                raise ChatMembershipError('permission_denied', 'Only the owner may transfer ownership.', 403)
            if target.user_id == current_owner.user_id:
                raise ChatMembershipError('invalid_transfer_target', 'Target is already the owner.', 400)
            old_target_role = target.role
            current_owner.role = ChatParticipant.ADMIN
            current_owner.role_updated_at = timezone.now()
            current_owner.save(update_fields=['role', 'role_updated_at'])
            target.role = ChatParticipant.OWNER
            target.role_updated_at = timezone.now()
            target.save(update_fields=['role', 'role_updated_at'])
            self._audit_membership(
                room,
                owner,
                target_user,
                ChatMembershipEvent.OWNERSHIP_TRANSFERRED,
                old_role=old_target_role,
                new_role=ChatParticipant.OWNER,
            )
            self._notify_membership(room, 'membership_updated', owner, ChatParticipant.ADMIN)
            self._notify_membership(room, 'membership_updated', target_user, ChatParticipant.OWNER)
            return target

    def leave_group(self, chat_room, user):
        with transaction.atomic():
            room = ChatRoom.objects.select_for_update().get(pk=chat_room.pk)
            self._require_group(room)
            membership = self._membership(room, user)
            participant_count = ChatParticipant.objects.filter(chat_room=room).count()
            if membership.role == ChatParticipant.OWNER and participant_count > 1:
                raise ChatMembershipError(
                    'ownership_transfer_required',
                    'Transfer ownership before leaving the room.',
                    409,
                )
            old_role = membership.role
            membership.delete()
            self._audit_membership(
                room,
                user,
                user,
                ChatMembershipEvent.MEMBER_LEFT,
                old_role=old_role,
            )
            if old_role == ChatParticipant.OWNER:
                room.status = ChatRoom.ARCHIVED
                room.save(update_fields=['status', 'updated_at'])
                self._audit_membership(
                    room,
                    user,
                    user,
                    ChatMembershipEvent.ROOM_ARCHIVED,
                    old_role=old_role,
                )
            self._notify_membership(room, 'membership_revoked', user)
            return room

    def archive_group(self, chat_room, actor):
        with transaction.atomic():
            room = ChatRoom.objects.select_for_update().get(pk=chat_room.pk)
            self._require_group(room)
            membership = self._membership(room, actor)
            if membership.role != ChatParticipant.OWNER:
                raise ChatMembershipError('permission_denied', 'Only the owner may archive the room.', 403)
            room.status = ChatRoom.ARCHIVED
            room.save(update_fields=['status', 'updated_at'])
            self._audit_membership(room, actor, actor, ChatMembershipEvent.ROOM_ARCHIVED)
            return room
    
    def _validate_and_process_file(self, file) -> Dict[str, Any]:
        """
        Validate and process uploaded file
        
        Args:
            file: Uploaded file
            
        Returns:
            Dict[str, Any]: File data
        """
        # Check file size
        if file.size > self.max_file_size:
            raise ValidationError(f"File size exceeds maximum allowed size of {self.max_file_size} bytes")
        
        # Check file type
        file_type = mimetypes.guess_type(file.name)[0]
        if file_type not in self.allowed_file_types:
            raise ValidationError(f"File type {file_type} is not allowed")
        
        return {
            'file': file,
            'file_name': file.name,
            'file_size': file.size,
            'file_type': file_type
        }
    
    def _mark_messages_as_delivered(self, messages: List[ChatMessage], user: User):
        """Mark messages as delivered for a user"""
        for message in messages:
            if message.sender != user and message.status == ChatMessage.SENT:
                message.mark_as_delivered()
    
    def _update_message_read_status(self, message: ChatMessage):
        """Update message read status based on participants"""
        # Count participants who have read the message
        read_count = ChatMessageRead.objects.filter(message=message).count()
        participant_count = message.chat_room.participants.count()
        
        # If all participants have read, mark as read
        if read_count >= participant_count - 1:  # -1 to exclude sender
            message.mark_as_read()
    
    def _update_message_analytics(self, chat_room: ChatRoom):
        """Update message analytics for a chat room"""
        if not getattr(settings, 'ANALYTICS_ENABLED', False):
            return

        try:
            analytics, _ = ChatAnalytics.objects.get_or_create(chat_room=chat_room)
            
            # Update message counts
            analytics.total_messages = ChatMessage.objects.filter(
                chat_room=chat_room,
                is_deleted=False
            ).count()
            
            today = timezone.now().date()
            analytics.messages_today = ChatMessage.objects.filter(
                chat_room=chat_room,
                sent_at__date=today,
                is_deleted=False
            ).count()
            
            week_ago = timezone.now() - timedelta(days=7)
            analytics.messages_this_week = ChatMessage.objects.filter(
                chat_room=chat_room,
                sent_at__gte=week_ago,
                is_deleted=False
            ).count()
            
            month_ago = timezone.now() - timedelta(days=30)
            analytics.messages_this_month = ChatMessage.objects.filter(
                chat_room=chat_room,
                sent_at__gte=month_ago,
                is_deleted=False
            ).count()
            
            # Update participant counts
            analytics.active_participants = ChatMessage.objects.filter(
                chat_room=chat_room,
                sent_at__gte=timezone.now() - timedelta(days=1),
                is_deleted=False,
            ).values('sender_id').distinct().count()
            
            analytics.new_participants_today = ChatParticipant.objects.filter(
                chat_room=chat_room,
                joined_at__date=today
            ).count()
            
            # Update file statistics
            file_messages = ChatMessage.objects.filter(
                chat_room=chat_room,
                message_type__in=[ChatMessage.IMAGE, ChatMessage.FILE, ChatMessage.AUDIO, ChatMessage.VIDEO],
                is_deleted=False
            )
            
            analytics.files_shared = file_messages.count()
            analytics.total_file_size = sum(
                msg.file_size or 0 for msg in file_messages
            )
            
            analytics.save()
            
        except Exception as e:
            logger.error(f"Error updating analytics: {e}")


class SupportService:
    """
    Support service for handling support tickets
    """
    
    def create_support_ticket(
        self,
        user: User,
        subject: str,
        description: str,
        category: str = SupportTicket.GENERAL,
        priority: str = SupportTicket.MEDIUM,
        **kwargs
    ) -> SupportTicket:
        """
        Create a new support ticket
        
        Args:
            user: User creating the ticket
            subject: Ticket subject
            description: Ticket description
            category: Ticket category
            priority: Ticket priority
            **kwargs: Additional ticket data
            
        Returns:
            SupportTicket: Created ticket
        """
        try:
            with transaction.atomic():
                # Create support chat room
                chat_room = ChatRoom.objects.create(
                    name=f"Support Ticket - {subject}",
                    room_type=ChatRoom.SUPPORT,
                    description=description,
                    created_by=user
                )
                
                # Create support ticket
                ticket = SupportTicket.objects.create(
                    user=user,
                    subject=subject,
                    description=description,
                    category=category,
                    priority=priority,
                    chat_room=chat_room,
                    **kwargs
                )
                
                # Add user as participant
                ChatParticipant.objects.create(
                    chat_room=chat_room,
                    user=user,
                )
                
                # Initialize analytics
                ChatAnalytics.objects.create(chat_room=chat_room)
                
                logger.info(f"Created support ticket {ticket.ticket_number}")
                return ticket
                
        except Exception as e:
            logger.error(f"Error creating support ticket: {e}")
            raise
    
    def assign_ticket(
        self,
        ticket: SupportTicket,
        agent: User,
        assigned_by: User
    ) -> bool:
        """
        Assign a support ticket to an agent
        
        Args:
            ticket: Support ticket
            agent: Agent to assign to
            assigned_by: User who is assigning
            
        Returns:
            bool: Success status
        """
        try:
            # Check if assigned_by has permission to assign tickets
            if not assigned_by.is_staff:
                raise ValidationError("Only staff members can assign tickets")
            
            # Assign ticket
            ticket.assign_to(agent)
            
            # Add agent as participant
            ChatParticipant.objects.get_or_create(
                chat_room=ticket.chat_room,
                user=agent,
            )
            
            logger.info("Assigned ticket %s to user %s", ticket.ticket_number, agent.pk)
            return True
            
        except Exception as e:
            logger.error(f"Error assigning ticket: {e}")
            raise
    
    def resolve_ticket(
        self,
        ticket: SupportTicket,
        resolution: str,
        resolved_by: User
    ) -> bool:
        """
        Resolve a support ticket
        
        Args:
            ticket: Support ticket
            resolution: Resolution description
            resolved_by: User who is resolving
            
        Returns:
            bool: Success status
        """
        try:
            # Check if resolved_by has permission
            if not resolved_by.is_staff and resolved_by != ticket.assigned_to:
                raise ValidationError("User is not authorized to resolve this ticket")
            
            # Resolve ticket
            ticket.resolve(resolution)
            
            logger.info(f"Resolved ticket {ticket.ticket_number}")
            return True
            
        except Exception as e:
            logger.error(f"Error resolving ticket: {e}")
            raise
    
    def get_ticket_stats(self, user: User = None) -> Dict[str, Any]:
        """
        Get support ticket statistics
        
        Args:
            user: User to filter by (if None, get all tickets)
            
        Returns:
            Dict[str, Any]: Statistics
        """
        try:
            query = Q()
            if user:
                query = Q(user=user)
            
            tickets = SupportTicket.objects.filter(query)
            
            stats = {
                'total_tickets': tickets.count(),
                'open_tickets': tickets.filter(status=SupportTicket.OPEN).count(),
                'in_progress_tickets': tickets.filter(status=SupportTicket.IN_PROGRESS).count(),
                'resolved_tickets': tickets.filter(status=SupportTicket.RESOLVED).count(),
                'closed_tickets': tickets.filter(status=SupportTicket.CLOSED).count(),
                'avg_resolution_time_hours': 0,
                'satisfaction_rating': 0,
            }
            
            # Calculate average resolution time
            resolved_tickets = tickets.filter(
                status=SupportTicket.RESOLVED,
                resolved_at__isnull=False
            )
            
            if resolved_tickets.exists():
                resolution_times = []
                for ticket in resolved_tickets:
                    if ticket.resolved_at and ticket.opened_at:
                        resolution_time = ticket.resolved_at - ticket.opened_at
                        resolution_times.append(resolution_time.total_seconds() / 3600)  # Convert to hours
                
                if resolution_times:
                    stats['avg_resolution_time_hours'] = sum(resolution_times) / len(resolution_times)
            
            # Calculate average satisfaction rating
            rated_tickets = tickets.filter(
                satisfaction_rating__isnull=False
            )
            
            if rated_tickets.exists():
                avg_rating = rated_tickets.aggregate(
                    avg_rating=Avg('satisfaction_rating')
                )['avg_rating']
                stats['satisfaction_rating'] = round(avg_rating, 2) if avg_rating else 0
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting ticket stats: {e}")
            return {}


class ChatAnalyticsService:
    """
    Service for chat analytics and reporting
    """
    
    def get_room_analytics(self, chat_room: ChatRoom) -> Dict[str, Any]:
        """
        Get analytics for a specific chat room
        
        Args:
            chat_room: Target chat room
            
        Returns:
            Dict[str, Any]: Analytics data
        """
        try:
            analytics = ChatAnalytics.objects.get(chat_room=chat_room)
            
            # Get recent activity
            recent_messages = ChatMessage.objects.filter(
                chat_room=chat_room,
                sent_at__gte=timezone.now() - timedelta(days=7)
            ).order_by('-sent_at')[:10]
            
            # Get top participants
            top_participants = ChatMessage.objects.filter(
                chat_room=chat_room,
                is_deleted=False
            ).values('sender__username').annotate(
                message_count=Count('id')
            ).order_by('-message_count')[:5]
            
            return {
                'room_info': {
                    'id': str(chat_room.id),
                    'name': chat_room.name,
                    'type': chat_room.room_type,
                    'created_at': chat_room.created_at,
                    'participant_count': chat_room.get_participant_count(),
                },
                'message_stats': {
                    'total_messages': analytics.total_messages,
                    'messages_today': analytics.messages_today,
                    'messages_this_week': analytics.messages_this_week,
                    'messages_this_month': analytics.messages_this_month,
                },
                'participant_stats': {
                    'active_participants': analytics.active_participants,
                    'new_participants_today': analytics.new_participants_today,
                },
                'file_stats': {
                    'files_shared': analytics.files_shared,
                    'total_file_size': analytics.total_file_size,
                    'total_file_size_mb': round(analytics.total_file_size / (1024 * 1024), 2),
                },
                'recent_messages': [
                    {
                        'id': str(msg.id),
                        'sender': msg.sender.username,
                        'content': msg.content[:100] + '...' if len(msg.content) > 100 else msg.content,
                        'message_type': msg.message_type,
                        'sent_at': msg.sent_at,
                    }
                    for msg in recent_messages
                ],
                'top_participants': list(top_participants),
                'last_calculated': analytics.last_calculated_at,
            }
            
        except Exception as e:
            logger.error(f"Error getting room analytics: {e}")
            return {}
    
    def get_global_analytics(self) -> Dict[str, Any]:
        """
        Get global chat analytics
        
        Returns:
            Dict[str, Any]: Global analytics data
        """
        try:
            # Get all chat rooms
            total_rooms = ChatRoom.objects.count()
            active_rooms = ChatRoom.objects.filter(
                status=ChatRoom.ACTIVE
            ).count()
            
            # Get all messages
            total_messages = ChatMessage.objects.filter(
                is_deleted=False
            ).count()
            
            messages_today = ChatMessage.objects.filter(
                sent_at__date=timezone.now().date(),
                is_deleted=False
            ).count()
            
            # Get support tickets
            total_tickets = SupportTicket.objects.count()
            open_tickets = SupportTicket.objects.filter(
                status=SupportTicket.OPEN
            ).count()
            
            # Get file sharing stats
            file_messages = ChatMessage.objects.filter(
                message_type__in=[ChatMessage.IMAGE, ChatMessage.FILE, ChatMessage.AUDIO, ChatMessage.VIDEO],
                is_deleted=False
            )
            
            total_files = file_messages.count()
            total_file_size = sum(msg.file_size or 0 for msg in file_messages)
            
            return {
                'room_stats': {
                    'total_rooms': total_rooms,
                    'active_rooms': active_rooms,
                    'archived_rooms': total_rooms - active_rooms,
                },
                'message_stats': {
                    'total_messages': total_messages,
                    'messages_today': messages_today,
                    'avg_messages_per_room': round(total_messages / total_rooms, 2) if total_rooms > 0 else 0,
                },
                'support_stats': {
                    'total_tickets': total_tickets,
                    'open_tickets': open_tickets,
                    'resolved_tickets': SupportTicket.objects.filter(
                        status=SupportTicket.RESOLVED
                    ).count(),
                },
                'file_stats': {
                    'total_files': total_files,
                    'total_file_size': total_file_size,
                    'total_file_size_mb': round(total_file_size / (1024 * 1024), 2),
                },
                'generated_at': timezone.now(),
            }
            
        except Exception as e:
            logger.error(f"Error getting global analytics: {e}")
            return {}
