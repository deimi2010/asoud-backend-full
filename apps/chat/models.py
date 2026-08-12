"""
Advanced Chat and Support Models for ASOUD Platform
Comprehensive chat system with real-time messaging, file sharing, and support tickets
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from apps.base.models import BaseModel
import uuid
import os

User = get_user_model()


def chat_user_display_name(user):
    """Return a non-sensitive display label for chat payloads."""
    full_name = user.get_full_name().strip()
    return full_name or f"User {user.pk}"


def chat_file_upload_path(instance, filename):
    """Generate upload path for chat files"""
    return f"chat/files/{instance.chat_room.id}/{filename}"


class ChatRoom(BaseModel):
    """
    Chat room for conversations between users
    """
    PRIVATE = 'private'
    GROUP = 'group'
    SUPPORT = 'support'
    MARKET = 'market'
    
    TYPE_CHOICES = [
        (PRIVATE, _('Private Chat')),
        (GROUP, _('Group Chat')),
        (SUPPORT, _('Support Chat')),
        (MARKET, _('Market Chat')),
    ]
    
    ACTIVE = 'active'
    ARCHIVED = 'archived'
    BLOCKED = 'blocked'
    
    STATUS_CHOICES = [
        (ACTIVE, _('Active')),
        (ARCHIVED, _('Archived')),
        (BLOCKED, _('Blocked')),
    ]
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    
    name = models.CharField(
        max_length=200,
        verbose_name=_('Room Name'),
        help_text=_('Name of the chat room'),
        default='Chat Room',
        null=True,
        blank=True
    )
    
    description = models.TextField(
        blank=True,
        verbose_name=_('Description'),
        help_text=_('Description of the chat room'),
        null=True
    )
    
    room_type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        default=PRIVATE,
        verbose_name=_('Room Type'),
        null=True,
        blank=True
    )
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=ACTIVE,
        verbose_name=_('Status')
    )
    
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        related_name='created_chat_rooms',
        verbose_name=_('Created By'),
        null=True,
        blank=True
    )
    
    participants = models.ManyToManyField(
        User,
        through='ChatParticipant',
        through_fields=('chat_room', 'user'),
        related_name='chat_rooms',
        verbose_name=_('Participants')
    )
    
    # Related object (e.g., Market, Order, etc.)
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_('Content Type')
    )
    
    object_id = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name=_('Object ID')
    )
    
    content_object = GenericForeignKey(
        'content_type',
        'object_id'
    )
    
    # Settings
    is_encrypted = models.BooleanField(
        default=False,
        verbose_name=_('Is Encrypted'),
        help_text=_('Whether messages in this room are encrypted')
    )
    
    allow_file_sharing = models.BooleanField(
        default=True,
        verbose_name=_('Allow File Sharing')
    )
    
    max_participants = models.PositiveIntegerField(
        default=100,
        verbose_name=_('Max Participants')
    )
    
    # Timestamps
    last_message_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Last Message At')
    )
    
    last_activity_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Last Activity At')
    )
    
    class Meta:
        db_table = 'chat_conversation'
        verbose_name = _('Chat Room')
        verbose_name_plural = _('Chat Rooms')
        ordering = ['-last_message_at', '-created_at']
        indexes = [
            models.Index(fields=['room_type', 'status']),
            models.Index(fields=['created_by']),
            models.Index(fields=['last_message_at']),
            models.Index(fields=['content_type', 'object_id']),
        ]
    
    def __str__(self):
        return f"{self.get_room_type_display()} - {self.name}"
    
    def get_participant_count(self):
        """Get number of participants"""
        return self.participants.count()
    
    def is_participant(self, user):
        """Check if user is a participant"""
        return self.participants.filter(id=user.id).exists()
    
    def add_participant(self, user, role='member'):
        """Add participant to room"""
        ChatParticipant.objects.get_or_create(
            chat_room=self,
            user=user,
            defaults={'role': role},
        )
    
    def remove_participant(self, user):
        """Remove participant from room"""
        ChatParticipant.objects.filter(
            chat_room=self,
            user=user
        ).delete()
    
    def update_last_activity(self):
        """Update last activity timestamp"""
        self.last_activity_at = timezone.now()
        self.save(update_fields=['last_activity_at'])


class ChatParticipant(models.Model):
    """
    Participants in chat rooms
    """
    OWNER = 'owner'
    ADMIN = 'admin'
    MEMBER = 'member'
    
    ROLE_CHOICES = [
        (OWNER, _('Owner')),
        (ADMIN, _('Admin')),
        (MEMBER, _('Member')),
    ]
    
    chat_room = models.ForeignKey(
        ChatRoom,
        on_delete=models.CASCADE,
        related_name='chat_participants',
        verbose_name=_('Chat Room'),
        db_column='chatconversation_id'
    )
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='chat_participants',
        verbose_name=_('User')
    )

    role = models.CharField(
        max_length=10,
        choices=ROLE_CHOICES,
        default=MEMBER,
        verbose_name=_('Role'),
    )

    joined_at = models.DateTimeField(default=timezone.now, editable=False)

    invited_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='invited_chat_participants',
        verbose_name=_('Invited By'),
    )

    role_updated_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        db_table = 'chat_conversation_participants'
        verbose_name = _('Chat Participant')
        verbose_name_plural = _('Chat Participants')
        unique_together = ['chat_room', 'user']
        ordering = ['joined_at', 'id']
        indexes = [models.Index(fields=['chat_room', 'role'])]
        constraints = [
            models.UniqueConstraint(
                fields=['chat_room'],
                condition=models.Q(role='owner'),
                name='chat_one_owner_per_room',
            ),
        ]
    
    def __str__(self):
        return f"{self.user.mobile_number} in {self.chat_room.name}"


class ChatMembershipEvent(models.Model):
    """Immutable audit record for group membership and role changes."""

    MEMBER_ADDED = 'member_added'
    MEMBER_REMOVED = 'member_removed'
    MEMBER_LEFT = 'member_left'
    ROLE_CHANGED = 'role_changed'
    OWNERSHIP_TRANSFERRED = 'ownership_transferred'
    ROOM_ARCHIVED = 'room_archived'

    ACTION_CHOICES = [
        (MEMBER_ADDED, _('Member added')),
        (MEMBER_REMOVED, _('Member removed')),
        (MEMBER_LEFT, _('Member left')),
        (ROLE_CHANGED, _('Role changed')),
        (OWNERSHIP_TRANSFERRED, _('Ownership transferred')),
        (ROOM_ARCHIVED, _('Room archived')),
    ]

    chat_room = models.ForeignKey(
        ChatRoom,
        on_delete=models.CASCADE,
        related_name='membership_events',
    )
    actor = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='chat_membership_actions',
    )
    subject = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='chat_membership_events',
    )
    action = models.CharField(max_length=32, choices=ACTION_CHOICES)
    old_role = models.CharField(max_length=10, choices=ChatParticipant.ROLE_CHOICES, null=True, blank=True)
    new_role = models.CharField(max_length=10, choices=ChatParticipant.ROLE_CHOICES, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'chat_membership_event'
        ordering = ['created_at', 'id']
        indexes = [models.Index(fields=['chat_room', 'created_at'])]


class ChatMessage(BaseModel):
    """
    Individual chat messages
    """
    TEXT = 'text'
    IMAGE = 'image'
    FILE = 'file'
    AUDIO = 'audio'
    VIDEO = 'video'
    LOCATION = 'location'
    SYSTEM = 'system'
    
    MESSAGE_TYPE_CHOICES = [
        (TEXT, _('Text')),
        (IMAGE, _('Image')),
        (FILE, _('File')),
        (AUDIO, _('Audio')),
        (VIDEO, _('Video')),
        (LOCATION, _('Location')),
        (SYSTEM, _('System')),
    ]
    
    SENT = 'sent'
    DELIVERED = 'delivered'
    READ = 'read'
    FAILED = 'failed'
    
    STATUS_CHOICES = [
        (SENT, _('Sent')),
        (DELIVERED, _('Delivered')),
        (READ, _('Read')),
        (FAILED, _('Failed')),
    ]
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    
    chat_room = models.ForeignKey(
        ChatRoom,
        on_delete=models.CASCADE,
        related_name='messages',
        verbose_name=_('Chat Room'),
        db_column='conversation_id',
        null=True,
        blank=True
    )
    
    sender = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='sent_messages',
        verbose_name=_('Sender')
    )
    
    message_type = models.CharField(
        max_length=20,
        choices=MESSAGE_TYPE_CHOICES,
        default=TEXT,
        verbose_name=_('Message Type')
    )
    
    content = models.TextField(
        verbose_name=_('Content'),
        help_text=_('Message content'),
        db_column='text',
        default=''
    )
    
    # File attachment
    file = models.FileField(
        upload_to=chat_file_upload_path,
        null=True,
        blank=True,
        verbose_name=_('File Attachment')
    )
    
    file_name = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=_('File Name')
    )
    
    file_size = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name=_('File Size (bytes)')
    )
    
    file_type = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name=_('File Type')
    )
    
    # Location data
    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        verbose_name=_('Latitude')
    )
    
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        verbose_name=_('Longitude')
    )
    
    # Message status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=SENT,
        verbose_name=_('Status')
    )
    
    is_read = models.BooleanField(
        default=False,
        verbose_name=_('Is Read')
    )
    
    # Reply to another message
    reply_to = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='replies',
        verbose_name=_('Reply To')
    )
    
    # Message metadata
    is_edited = models.BooleanField(
        default=False,
        verbose_name=_('Is Edited')
    )
    
    edited_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Edited At')
    )
    
    is_deleted = models.BooleanField(
        default=False,
        verbose_name=_('Is Deleted')
    )
    
    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Deleted At')
    )
    
    # Encryption
    is_encrypted = models.BooleanField(
        default=False,
        verbose_name=_('Is Encrypted')
    )
    
    encryption_key = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=_('Encryption Key')
    )
    
    # Timestamps
    sent_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Sent At')
    )
    
    delivered_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Delivered At')
    )
    
    read_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Read At')
    )
    
    # Retry and priority fields
    max_retries = models.PositiveIntegerField(
        default=3,
        verbose_name=_('Max Retries')
    )
    
    retry_count = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Retry Count')
    )
    
    priority = models.CharField(
        max_length=10,
        choices=[('high', 'High'), ('medium', 'Medium'), ('low', 'Low')],
        default='medium',
        verbose_name=_('Priority')
    )
    
    # Failure tracking
    failure_reason = models.TextField(
        null=True,
        blank=True,
        verbose_name=_('Failure Reason')
    )
    
    scheduled_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Scheduled At')
    )
    
    class Meta:
        db_table = 'chat_message'
        verbose_name = _('Chat Message')
        verbose_name_plural = _('Chat Messages')
        ordering = ['-sent_at']
        indexes = [
            models.Index(fields=['chat_room', 'sent_at']),
            models.Index(fields=['sender']),
            models.Index(fields=['message_type']),
            models.Index(fields=['status']),
            models.Index(fields=['reply_to']),
        ]
    
    def __str__(self):
        return f"{self.sender.mobile_number}: {self.content[:50]}..."
    
    def mark_as_delivered(self):
        """Mark message as delivered"""
        self.status = self.DELIVERED
        self.delivered_at = timezone.now()
        self.save(update_fields=['status', 'delivered_at'])
    
    def mark_as_read(self):
        """Mark message as read"""
        self.status = self.READ
        self.read_at = timezone.now()
        self.save(update_fields=['status', 'read_at'])
    
    def mark_as_failed(self):
        """Mark message as failed"""
        self.status = self.FAILED
        self.save(update_fields=['status'])
    
    def edit_message(self, new_content):
        """Edit message content"""
        self.content = new_content
        self.is_edited = True
        self.edited_at = timezone.now()
        self.save(update_fields=['content', 'is_edited', 'edited_at'])
    
    def delete_message(self):
        """Soft delete message"""
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(update_fields=['is_deleted', 'deleted_at'])


class ChatMessageRead(BaseModel):
    """
    Track which users have read which messages
    """
    message = models.ForeignKey(
        ChatMessage,
        on_delete=models.CASCADE,
        related_name='read_by',
        verbose_name=_('Message')
    )
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='read_messages',
        verbose_name=_('User')
    )
    
    read_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Read At')
    )
    
    class Meta:
        db_table = 'chat_chatmessageread'
        verbose_name = _('Message Read')
        verbose_name_plural = _('Messages Read')
        unique_together = ['message', 'user']
        ordering = ['-read_at']
    
    def __str__(self):
        return f"User {self.user_id} read {self.message_id}"


class SupportTicket(BaseModel):
    """
    Support tickets for customer service
    """
    LOW = 'low'
    MEDIUM = 'medium'
    HIGH = 'high'
    URGENT = 'urgent'
    
    PRIORITY_CHOICES = [
        (LOW, _('Low')),
        (MEDIUM, _('Medium')),
        (HIGH, _('High')),
        (URGENT, _('Urgent')),
    ]
    
    OPEN = 'open'
    IN_PROGRESS = 'in_progress'
    PENDING_CUSTOMER = 'pending_customer'
    PENDING_AGENT = 'pending_agent'
    RESOLVED = 'resolved'
    CLOSED = 'closed'
    
    STATUS_CHOICES = [
        (OPEN, _('Open')),
        (IN_PROGRESS, _('In Progress')),
        (PENDING_CUSTOMER, _('Pending Customer')),
        (PENDING_AGENT, _('Pending Agent')),
        (RESOLVED, _('Resolved')),
        (CLOSED, _('Closed')),
    ]
    
    TECHNICAL = 'technical'
    BILLING = 'billing'
    GENERAL = 'general'
    COMPLAINT = 'complaint'
    FEATURE_REQUEST = 'feature_request'
    
    CATEGORY_CHOICES = [
        (TECHNICAL, _('Technical')),
        (BILLING, _('Billing')),
        (GENERAL, _('General')),
        (COMPLAINT, _('Complaint')),
        (FEATURE_REQUEST, _('Feature Request')),
    ]
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    
    ticket_number = models.CharField(
        max_length=20,
        unique=True,
        verbose_name=_('Ticket Number')
    )
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='support_tickets',
        verbose_name=_('User')
    )
    
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_tickets',
        verbose_name=_('Assigned To')
    )
    
    subject = models.CharField(
        max_length=200,
        verbose_name=_('Subject')
    )
    
    description = models.TextField(
        verbose_name=_('Description')
    )
    
    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        default=GENERAL,
        verbose_name=_('Category')
    )
    
    priority = models.CharField(
        max_length=20,
        choices=PRIORITY_CHOICES,
        default=MEDIUM,
        verbose_name=_('Priority')
    )
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=OPEN,
        verbose_name=_('Status')
    )
    
    # Related chat room
    chat_room = models.OneToOneField(
        ChatRoom,
        on_delete=models.CASCADE,
        related_name='support_ticket',
        verbose_name=_('Chat Room')
    )
    
    # Timestamps
    opened_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Opened At')
    )
    
    last_activity_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Last Activity At')
    )
    
    resolved_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Resolved At')
    )
    
    closed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Closed At')
    )
    
    # Resolution
    resolution = models.TextField(
        null=True,
        blank=True,
        verbose_name=_('Resolution')
    )
    
    satisfaction_rating = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name=_('Satisfaction Rating'),
        help_text=_('Rating from 1 to 5')
    )
    
    satisfaction_feedback = models.TextField(
        null=True,
        blank=True,
        verbose_name=_('Satisfaction Feedback')
    )
    
    class Meta:
        db_table = 'chat_supportticket'
        verbose_name = _('Support Ticket')
        verbose_name_plural = _('Support Tickets')
        ordering = ['-opened_at']
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['assigned_to']),
            models.Index(fields=['status']),
            models.Index(fields=['priority']),
            models.Index(fields=['category']),
            models.Index(fields=['ticket_number']),
        ]
    
    def __str__(self):
        return f"#{self.ticket_number} - {self.subject}"
    
    def save(self, *args, **kwargs):
        if not self.ticket_number:
            self.ticket_number = self.generate_ticket_number()
        super().save(*args, **kwargs)
    
    def generate_ticket_number(self):
        """Generate unique ticket number"""
        import random
        import string
        
        while True:
            ticket_number = f"TK{''.join(random.choices(string.digits, k=8))}"
            if not SupportTicket.objects.filter(ticket_number=ticket_number).exists():
                return ticket_number
    
    def assign_to(self, agent):
        """Assign ticket to agent"""
        self.assigned_to = agent
        self.status = self.IN_PROGRESS
        self.save(update_fields=['assigned_to', 'status'])
    
    def resolve(self, resolution):
        """Resolve ticket"""
        self.status = self.RESOLVED
        self.resolution = resolution
        self.resolved_at = timezone.now()
        self.save(update_fields=['status', 'resolution', 'resolved_at'])
    
    def close(self):
        """Close ticket"""
        self.status = self.CLOSED
        self.closed_at = timezone.now()
        self.save(update_fields=['status', 'closed_at'])
    
    def update_activity(self):
        """Update last activity timestamp"""
        self.last_activity_at = timezone.now()
        self.save(update_fields=['last_activity_at'])


class ChatAnalytics(BaseModel):
    """
    Analytics for chat rooms and messages
    """
    chat_room = models.ForeignKey(
        ChatRoom,
        on_delete=models.CASCADE,
        related_name='analytics',
        verbose_name=_('Chat Room')
    )
    
    # Message statistics
    total_messages = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Total Messages')
    )
    
    messages_today = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Messages Today')
    )
    
    messages_this_week = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Messages This Week')
    )
    
    messages_this_month = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Messages This Month')
    )
    
    # User statistics
    active_participants = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Active Participants')
    )
    
    new_participants_today = models.PositiveIntegerField(
        default=0,
        verbose_name=_('New Participants Today')
    )
    
    # Response time
    avg_response_time_minutes = models.FloatField(
        default=0,
        verbose_name=_('Average Response Time (minutes)')
    )
    
    # File sharing
    files_shared = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Files Shared')
    )
    
    total_file_size = models.PositiveBigIntegerField(
        default=0,
        verbose_name=_('Total File Size (bytes)')
    )
    
    # Timestamps
    last_calculated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Last Calculated At')
    )
    
    class Meta:
        db_table = 'chat_chatanalytics'
        verbose_name = _('Chat Analytics')
        verbose_name_plural = _('Chat Analytics')
        unique_together = ['chat_room']
    
    def __str__(self):
        return f"Analytics for {self.chat_room.name}"
