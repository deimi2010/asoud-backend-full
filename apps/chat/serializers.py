"""
Advanced Chat and Support Serializers for ASOUD Platform
Serializers for chat rooms, messages, and support tickets
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
import base64
import mimetypes
import uuid

from .models import (
    ChatRoom, ChatParticipant, ChatMessage, ChatMessageRead,
    SupportTicket, ChatAnalytics, chat_user_display_name
)

User = get_user_model()


class ChatRoomSerializer(serializers.ModelSerializer):
    """
    Serializer for chat rooms
    """
    created_by_username = serializers.SerializerMethodField()
    participant_count = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    current_user_role = serializers.SerializerMethodField()
    capabilities = serializers.SerializerMethodField()
    
    class Meta:
        model = ChatRoom
        fields = [
            'id', 'name', 'description', 'room_type', 'status',
            'created_by', 'created_by_username', 'created_at',
            'last_message_at', 'last_activity_at',
            'participant_count', 'last_message', 'unread_count',
            'current_user_role', 'capabilities',
            'is_encrypted', 'allow_file_sharing', 'max_participants',
            'content_type', 'object_id'
        ]
        read_only_fields = ['id', 'created_at', 'last_message_at', 'last_activity_at']
    
    def get_participant_count(self, obj):
        """Get number of participants"""
        return obj.get_participant_count()
    
    def get_last_message(self, obj):
        """Get last message in room"""
        last_message = obj.messages.filter(is_deleted=False).first()
        if last_message:
            return {
                'id': str(last_message.id),
                'sender_username': chat_user_display_name(last_message.sender),
                'content': last_message.content[:100] + '...' if len(last_message.content) > 100 else last_message.content,
                'message_type': last_message.message_type,
                'sent_at': last_message.sent_at,
            }
        return None
    
    def get_unread_count(self, obj):
        """Get unread message count for current user"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            from .services import ChatService
            chat_service = ChatService()
            return chat_service.get_unread_count(obj, request.user)
        return 0
    
    def get_created_by_username(self, obj):
        if not obj.created_by:
            return None
        return chat_user_display_name(obj.created_by)

    def _membership(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return None
        return obj.chat_participants.filter(user=request.user).first()

    def get_current_user_role(self, obj):
        membership = self._membership(obj)
        return membership.role if membership else None

    def get_capabilities(self, obj):
        membership = self._membership(obj)
        role = membership.role if membership else None
        is_group = obj.room_type == ChatRoom.GROUP
        return {
            'can_manage_members': is_group and role in (ChatParticipant.OWNER, ChatParticipant.ADMIN),
            'can_manage_admins': is_group and role == ChatParticipant.OWNER,
            'can_transfer_ownership': is_group and role == ChatParticipant.OWNER,
            'can_update_metadata': is_group and role in (ChatParticipant.OWNER, ChatParticipant.ADMIN),
            'can_manage_settings': is_group and role == ChatParticipant.OWNER,
            'can_leave': is_group and role is not None,
        }


class ChatRoomCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating chat rooms
    """
    participants = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        many=True,
        write_only=True,
        required=False
    )
    
    class Meta:
        model = ChatRoom
        fields = [
            'id', 'name', 'description', 'room_type', 'participants',
            'is_encrypted', 'allow_file_sharing', 'max_participants',
            'content_type', 'object_id'
        ]
        read_only_fields = ['id']
    
    def validate_max_participants(self, value):
        """Validate max participants"""
        if value < 2:
            raise serializers.ValidationError("Maximum participants must be at least 2")
        platform_cap = getattr(settings, 'CHAT_GROUP_MAX_PARTICIPANTS', 100)
        if value > platform_cap:
            raise serializers.ValidationError(
                f"Maximum participants cannot exceed the platform limit ({platform_cap})"
            )
        return value

    def validate(self, attrs):
        room_type = attrs.get('room_type', ChatRoom.PRIVATE)
        participants = attrs.get('participants', [])
        if room_type in (ChatRoom.SUPPORT, ChatRoom.MARKET):
            raise serializers.ValidationError({
                'room_type': 'Support and market rooms are system-managed.'
            })
        if room_type == ChatRoom.PRIVATE and len(participants) != 1:
            raise serializers.ValidationError({
                'participants': 'A private room requires exactly one other participant.'
            })
        if room_type == ChatRoom.GROUP and participants:
            raise serializers.ValidationError({
                'participants': (
                    'Create the group first, then invite members by exact mobile number.'
                )
            })
        return attrs


class ChatRoomUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating chat rooms
    """
    class Meta:
        model = ChatRoom
        fields = [
            'name', 'description', 'status', 'is_encrypted',
            'allow_file_sharing', 'max_participants'
        ]
    
    def validate_max_participants(self, value):
        """Validate max participants"""
        if value < 2:
            raise serializers.ValidationError("Maximum participants must be at least 2")
        
        # Check if new limit is less than current participant count
        if self.instance and value < self.instance.get_participant_count():
            raise serializers.ValidationError(
                f"Maximum participants cannot be less than current participant count ({self.instance.get_participant_count()})"
            )
        platform_cap = getattr(settings, 'CHAT_GROUP_MAX_PARTICIPANTS', 100)
        if value > platform_cap:
            raise serializers.ValidationError(
                f"Maximum participants cannot exceed the platform limit ({platform_cap})"
            )
        return value


class ChatParticipantSerializer(serializers.ModelSerializer):
    """
    Serializer for chat participants
    """
    username = serializers.SerializerMethodField()
    first_name = serializers.CharField(source='user.first_name', read_only=True)
    last_name = serializers.CharField(source='user.last_name', read_only=True)
    class Meta:
        model = ChatParticipant
        fields = [
            'id', 'user', 'username', 'first_name', 'last_name', 'role',
            'joined_at', 'role_updated_at',
        ]
        read_only_fields = ['id']
    
    def get_username(self, obj):
        return chat_user_display_name(obj.user)


class ChatMessageSerializer(serializers.ModelSerializer):
    """
    Serializer for chat messages
    """
    sender_username = serializers.SerializerMethodField()
    sender_first_name = serializers.CharField(source='sender.first_name', read_only=True)
    sender_last_name = serializers.CharField(source='sender.last_name', read_only=True)
    reply_to_content = serializers.SerializerMethodField()
    reply_to_sender = serializers.SerializerMethodField()
    file_url = serializers.SerializerMethodField()
    file_size_mb = serializers.SerializerMethodField()
    is_edited = serializers.BooleanField(read_only=True)
    edited_at = serializers.DateTimeField(read_only=True)
    read_by = serializers.SerializerMethodField()
    
    class Meta:
        model = ChatMessage
        fields = [
            'id', 'chat_room', 'sender', 'sender_username', 'sender_first_name', 'sender_last_name',
            'message_type', 'content', 'file', 'file_name', 'file_size', 'file_size_mb',
            'file_type', 'file_url', 'latitude', 'longitude', 'status',
            'reply_to', 'reply_to_content', 'reply_to_sender',
            'is_edited', 'edited_at', 'is_deleted', 'sent_at',
            'delivered_at', 'read_at', 'read_by'
        ]
        read_only_fields = [
            'id', 'sent_at', 'delivered_at', 'read_at', 'status',
            'is_edited', 'edited_at', 'is_deleted'
        ]
    
    def get_reply_to_content(self, obj):
        """Get reply to message content"""
        if obj.reply_to:
            return obj.reply_to.content[:100] + '...' if len(obj.reply_to.content) > 100 else obj.reply_to.content
        return None
    
    def get_reply_to_sender(self, obj):
        """Get reply to message sender"""
        if obj.reply_to:
            return chat_user_display_name(obj.reply_to.sender)
        return None

    def get_sender_username(self, obj):
        return chat_user_display_name(obj.sender)
    
    def get_file_url(self, obj):
        """Get file URL"""
        if obj.file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.file.url)
            return obj.file.url
        return None
    
    def get_file_size_mb(self, obj):
        """Get file size in MB"""
        if obj.file_size:
            return round(obj.file_size / (1024 * 1024), 2)
        return None
    
    def get_read_by(self, obj):
        """Get users who have read this message"""
        read_by = ChatMessageRead.objects.filter(message=obj).select_related('user')
        return [
            {
                'user_id': read.user.id,
                'username': chat_user_display_name(read.user),
                'read_at': read.read_at
            }
            for read in read_by
        ]


class ChatMessageCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating chat messages
    """
    file_data = serializers.CharField(write_only=True, required=False)
    
    class Meta:
        model = ChatMessage
        fields = [
            'id', 'chat_room_id', 'sender', 'content', 'message_type',
            'file_data', 'reply_to', 'latitude', 'longitude', 'status',
            'sent_at',
        ]
        read_only_fields = ['id', 'sender', 'status', 'sent_at']
    
    def validate_message_type(self, value):
        """Validate message type"""
        valid_types = [choice[0] for choice in ChatMessage.MESSAGE_TYPE_CHOICES]
        if value not in valid_types:
            raise serializers.ValidationError(f"Invalid message type. Must be one of: {valid_types}")
        return value
    
    def validate_file_data(self, value):
        """Validate file data"""
        if not value:
            return value
        
        try:
            # Parse base64 file data
            file_info = value.split(',')
            if len(file_info) != 2:
                raise serializers.ValidationError("Invalid file data format")
            
            file_type, file_content = file_info
            if not file_type.startswith('data:'):
                raise serializers.ValidationError("Invalid file data format")
            
            # Extract MIME type
            mime_type = file_type.split(';')[0].split(':')[1]
            
            # Validate file type
            allowed_types = [
                'image/jpeg', 'image/png', 'image/gif', 'image/webp',
                'application/pdf', 'text/plain', 'application/msword',
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                'audio/mpeg', 'audio/wav', 'video/mp4', 'video/avi'
            ]
            
            if mime_type not in allowed_types:
                raise serializers.ValidationError(f"File type {mime_type} is not allowed")
            
            return value
            
        except Exception as e:
            raise serializers.ValidationError(f"Invalid file data: {str(e)}")
    
    def create(self, validated_data):
        """Create chat message with file handling"""
        file_data = validated_data.pop('file_data', None)
        chat_room_id = validated_data.pop('chat_room_id')
        
        # Get chat room
        try:
            chat_room = ChatRoom.objects.get(id=chat_room_id)
        except ChatRoom.DoesNotExist:
            raise serializers.ValidationError("Chat room not found")
        
        # Process file if provided
        file_obj = None
        if file_data:
            file_obj = self._process_file_data(file_data)
        
        # Create message using service
        from .services import ChatService
        chat_service = ChatService()
        
        message = chat_service.send_message(
            chat_room=chat_room,
            sender=self.context['request'].user,
            content=validated_data['content'],
            message_type=validated_data.get('message_type', ChatMessage.TEXT),
            file=file_obj,
            reply_to=validated_data.get('reply_to')
        )
        
        return message
    
    def _process_file_data(self, file_data):
        """Process base64 file data"""
        try:
            file_info = file_data.split(',')
            file_type, file_content = file_info
            
            # Extract MIME type and filename
            mime_type = file_type.split(';')[0].split(':')[1]
            extension = mimetypes.guess_extension(mime_type) or '.bin'
            filename = f"file_{uuid.uuid4().hex}{extension}"
            
            # Decode base64 content
            file_content = base64.b64decode(file_content)
            
            # Create file object
            file_obj = ContentFile(file_content, name=filename)
            
            return file_obj
            
        except Exception as e:
            raise serializers.ValidationError(f"Error processing file: {str(e)}")


class SupportTicketSerializer(serializers.ModelSerializer):
    """
    Serializer for support tickets
    """
    user_username = serializers.SerializerMethodField()
    assigned_to_username = serializers.SerializerMethodField()
    ticket_number = serializers.CharField(read_only=True)
    chat_room_id = serializers.UUIDField(source='chat_room.id', read_only=True)
    opened_at = serializers.DateTimeField(read_only=True)
    last_activity_at = serializers.DateTimeField(read_only=True)
    resolved_at = serializers.DateTimeField(read_only=True)
    closed_at = serializers.DateTimeField(read_only=True)
    
    class Meta:
        model = SupportTicket
        fields = [
            'id', 'ticket_number', 'user', 'user_username', 'assigned_to', 'assigned_to_username',
            'subject', 'description', 'category', 'priority', 'status',
            'chat_room_id', 'opened_at', 'last_activity_at', 'resolved_at', 'closed_at',
            'resolution', 'satisfaction_rating', 'satisfaction_feedback'
        ]
        read_only_fields = [
            'id', 'ticket_number', 'opened_at', 'last_activity_at',
            'resolved_at', 'closed_at'
        ]

    def get_user_username(self, obj):
        return chat_user_display_name(obj.user)

    def get_assigned_to_username(self, obj):
        if not obj.assigned_to:
            return None
        return chat_user_display_name(obj.assigned_to)


class SupportTicketCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating support tickets
    """
    class Meta:
        model = SupportTicket
        fields = [
            'subject', 'description', 'category', 'priority'
        ]
    
    def validate_subject(self, value):
        """Validate subject"""
        if len(value.strip()) < 5:
            raise serializers.ValidationError("Subject must be at least 5 characters long")
        return value.strip()
    
    def validate_description(self, value):
        """Validate description"""
        if len(value.strip()) < 10:
            raise serializers.ValidationError("Description must be at least 10 characters long")
        return value.strip()


class SupportTicketUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating support tickets
    """
    class Meta:
        model = SupportTicket
        fields = [
            'status', 'priority', 'assigned_to', 'resolution',
            'satisfaction_rating', 'satisfaction_feedback'
        ]
    
    def validate_satisfaction_rating(self, value):
        """Validate satisfaction rating"""
        if value is not None and (value < 1 or value > 5):
            raise serializers.ValidationError("Satisfaction rating must be between 1 and 5")
        return value


class ChatAnalyticsSerializer(serializers.ModelSerializer):
    """
    Serializer for chat analytics
    """
    room_name = serializers.CharField(source='chat_room.name', read_only=True)
    room_type = serializers.CharField(source='chat_room.room_type', read_only=True)
    total_file_size_mb = serializers.SerializerMethodField()
    
    class Meta:
        model = ChatAnalytics
        fields = [
            'id', 'chat_room', 'room_name', 'room_type',
            'total_messages', 'messages_today', 'messages_this_week', 'messages_this_month',
            'active_participants', 'new_participants_today',
            'avg_response_time_minutes', 'files_shared', 'total_file_size',
            'total_file_size_mb', 'last_calculated_at'
        ]
        read_only_fields = ['id', 'last_calculated_at']
    
    def get_total_file_size_mb(self, obj):
        """Get total file size in MB"""
        if obj.total_file_size:
            return round(obj.total_file_size / (1024 * 1024), 2)
        return 0


class ChatMessageReadSerializer(serializers.ModelSerializer):
    """
    Serializer for message read status
    """
    user_username = serializers.SerializerMethodField()
    
    class Meta:
        model = ChatMessageRead
        fields = [
            'id', 'message', 'user', 'user_username', 'read_at'
        ]
        read_only_fields = ['id', 'read_at']

    def get_user_username(self, obj):
        return chat_user_display_name(obj.user)


class ChatRoomSearchSerializer(serializers.Serializer):
    """
    Serializer for chat room search
    """
    query = serializers.CharField(max_length=255)
    room_type = serializers.ChoiceField(
        choices=ChatRoom.TYPE_CHOICES,
        required=False
    )
    status = serializers.ChoiceField(
        choices=ChatRoom.STATUS_CHOICES,
        required=False
    )


class ChatMessageSearchSerializer(serializers.Serializer):
    """
    Serializer for chat message search
    """
    query = serializers.CharField(max_length=255)
    room_id = serializers.UUIDField(required=False)
    message_type = serializers.ChoiceField(
        choices=ChatMessage.MESSAGE_TYPE_CHOICES,
        required=False
    )
    date_from = serializers.DateTimeField(required=False)
    date_to = serializers.DateTimeField(required=False)


class SupportTicketStatsSerializer(serializers.Serializer):
    """
    Serializer for support ticket statistics
    """
    total_tickets = serializers.IntegerField()
    open_tickets = serializers.IntegerField()
    in_progress_tickets = serializers.IntegerField()
    resolved_tickets = serializers.IntegerField()
    closed_tickets = serializers.IntegerField()
    avg_resolution_time_hours = serializers.FloatField()
    satisfaction_rating = serializers.FloatField()


class ChatRoomInviteSerializer(serializers.Serializer):
    """
    Serializer for inviting users to chat room
    """
    user_ids = serializers.ListField(
        child=serializers.IntegerField(),
        min_length=1
    )
    def validate_user_ids(self, value):
        """Validate user IDs"""
        if not value:
            raise serializers.ValidationError("At least one user ID is required")
        
        # Check if all user IDs exist
        user_ids = set(value)
        existing_users = User.objects.filter(id__in=user_ids).values_list('id', flat=True)
        
        if len(existing_users) != len(user_ids):
            missing_ids = user_ids - set(existing_users)
            raise serializers.ValidationError(f"Users with IDs {missing_ids} do not exist")
        
        return value


class ChatRoomLeaveSerializer(serializers.Serializer):
    """
    Serializer for leaving chat room
    """
    confirm = serializers.BooleanField(required=True)
    
    def validate_confirm(self, value):
        """Validate confirmation"""
        if not value:
            raise serializers.ValidationError("You must confirm to leave the chat room")
        return value
