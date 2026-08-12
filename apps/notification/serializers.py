"""
Notification Serializers for ASOUD Platform
Serializers for notification models and API responses
"""

from rest_framework import serializers
from django.utils import timezone
from django.contrib.auth import get_user_model
from .models import (
    Notification, NotificationTemplate, NotificationPreference,
    NotificationLog, NotificationQueue
)

User = get_user_model()


class NotificationTemplateSerializer(serializers.ModelSerializer):
    """
    Serializer for notification templates
    """
    notification_type_display = serializers.CharField(
        source='get_notification_type_display',
        read_only=True
    )
    channel_display = serializers.CharField(
        source='get_channel_display',
        read_only=True
    )
    
    class Meta:
        model = NotificationTemplate
        fields = [
            'id', 'name', 'notification_type', 'notification_type_display',
            'channel', 'channel_display', 'subject', 'title', 'body',
            'is_active', 'variables', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    """
    Serializer for user notification preferences
    """
    user_username = serializers.CharField(
        source='user.username',
        read_only=True
    )
    
    class Meta:
        model = NotificationPreference
        fields = [
            'id', 'user', 'user_username',
            'push_enabled', 'push_orders', 'push_messages', 'push_marketing', 'push_system',
            'email_enabled', 'email_orders', 'email_messages', 'email_marketing', 'email_system',
            'sms_enabled', 'sms_orders', 'sms_messages', 'sms_marketing', 'sms_system',
            'quiet_hours_start', 'quiet_hours_end', 'timezone',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']


class NotificationSerializer(serializers.ModelSerializer):
    """
    Serializer for notifications
    """
    user_username = serializers.CharField(
        source='user.username',
        read_only=True
    )
    notification_type_display = serializers.CharField(
        source='get_notification_type_display',
        read_only=True
    )
    channel_display = serializers.CharField(
        source='get_channel_display',
        read_only=True
    )
    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True
    )
    priority_display = serializers.CharField(
        source='get_priority_display',
        read_only=True
    )
    content_object_name = serializers.SerializerMethodField()
    is_read = serializers.SerializerMethodField()
    
    class Meta:
        model = Notification
        fields = [
            'id', 'user', 'user_username', 'template', 'notification_type',
            'notification_type_display', 'channel', 'channel_display',
            'title', 'body', 'data', 'status', 'status_display',
            'priority', 'priority_display', 'scheduled_at', 'sent_at',
            'delivered_at', 'read_at', 'failure_reason', 'retry_count',
            'max_retries', 'content_object_name', 'is_read',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'user', 'sent_at', 'delivered_at', 'read_at',
            'failure_reason', 'retry_count', 'created_at', 'updated_at'
        ]
    
    def get_content_object_name(self, obj) -> str:
        """Get the name of the content object"""
        if obj.content_object:
            if hasattr(obj.content_object, 'name'):
                return str(obj.content_object.name)
            elif hasattr(obj.content_object, 'title'):
                return str(obj.content_object.title)
            elif hasattr(obj.content_object, 'username'):
                return str(obj.content_object.username)
        return ""
    
    def get_is_read(self, obj) -> bool:
        """Check if notification is read"""
        return obj.status == Notification.READ


class NotificationCreateSerializer(serializers.Serializer):
    """
    Serializer for creating notifications
    """
    user_id = serializers.IntegerField()
    notification_type = serializers.ChoiceField(
        choices=NotificationTemplate.TYPE_CHOICES
    )
    title = serializers.CharField(max_length=200)
    body = serializers.CharField()
    channel = serializers.ChoiceField(
        choices=NotificationTemplate.CHANNEL_CHOICES,
        default='websocket'
    )
    data = serializers.JSONField(required=False, default=dict)
    priority = serializers.ChoiceField(
        choices=Notification.PRIORITY_CHOICES,
        default='medium'
    )
    scheduled_at = serializers.DateTimeField(required=False)
    content_type = serializers.CharField(required=False)
    object_id = serializers.IntegerField(required=False)
    
    def validate_user_id(self, value):
        """Validate user exists"""
        try:
            User.objects.get(id=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("User not found")
        return value


class NotificationUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating notifications
    """
    
    class Meta:
        model = Notification
        fields = ['title', 'body', 'data', 'priority', 'scheduled_at']
    
    def validate_scheduled_at(self, value):
        """Validate scheduled time is in future"""
        if value and value <= timezone.now():
            raise serializers.ValidationError("Scheduled time must be in the future")
        return value


class NotificationLogSerializer(serializers.ModelSerializer):
    """
    Serializer for notification logs
    """
    notification_title = serializers.CharField(
        source='notification.title',
        read_only=True
    )
    status_display = serializers.CharField(
        source='get_status_display',
        read_only=True
    )
    
    class Meta:
        model = NotificationLog
        fields = [
            'id', 'notification', 'notification_title', 'attempt_number',
            'status', 'status_display', 'response_data', 'error_message',
            'duration_ms', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class NotificationQueueSerializer(serializers.ModelSerializer):
    """
    Serializer for notification queue
    """
    notification_title = serializers.CharField(
        source='notification.title',
        read_only=True
    )
    notification_user = serializers.CharField(
        source='notification.user.username',
        read_only=True
    )
    
    class Meta:
        model = NotificationQueue
        fields = [
            'id', 'notification', 'notification_title', 'notification_user',
            'priority', 'scheduled_at', 'is_processing', 'processing_started_at',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class NotificationStatsSerializer(serializers.Serializer):
    """
    Serializer for notification statistics
    """
    total_notifications = serializers.IntegerField()
    sent_notifications = serializers.IntegerField()
    delivered_notifications = serializers.IntegerField()
    failed_notifications = serializers.IntegerField()
    pending_notifications = serializers.IntegerField()
    read_notifications = serializers.IntegerField()
    
    # Channel breakdown
    push_notifications = serializers.IntegerField()
    email_notifications = serializers.IntegerField()
    sms_notifications = serializers.IntegerField()
    websocket_notifications = serializers.IntegerField()
    
    # Type breakdown
    order_notifications = serializers.IntegerField()
    message_notifications = serializers.IntegerField()
    marketing_notifications = serializers.IntegerField()
    system_notifications = serializers.IntegerField()
    
    # Performance metrics
    average_delivery_time = serializers.FloatField()
    success_rate = serializers.FloatField()
    retry_rate = serializers.FloatField()


class NotificationTemplateCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating notification templates
    """
    
    class Meta:
        model = NotificationTemplate
        fields = [
            'name', 'notification_type', 'channel', 'subject',
            'title', 'body', 'is_active', 'variables'
        ]
    
    def validate_name(self, value):
        """Validate template name is unique"""
        if NotificationTemplate.objects.filter(name=value).exists():
            raise serializers.ValidationError("Template with this name already exists")
        return value
    
    def validate(self, data):
        """Validate template data"""
        # Check unique constraint
        if NotificationTemplate.objects.filter(
            notification_type=data['notification_type'],
            channel=data['channel']
        ).exists():
            raise serializers.ValidationError(
                "Template for this notification type and channel already exists"
            )
        return data


class NotificationPreferenceUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating notification preferences
    """
    
    class Meta:
        model = NotificationPreference
        fields = [
            'push_enabled', 'push_orders', 'push_messages', 'push_marketing', 'push_system',
            'email_enabled', 'email_orders', 'email_messages', 'email_marketing', 'email_system',
            'sms_enabled', 'sms_orders', 'sms_messages', 'sms_marketing', 'sms_system',
            'quiet_hours_start', 'quiet_hours_end', 'timezone'
        ]
    
    def validate_quiet_hours_start(self, value):
        """Validate quiet hours start time"""
        if value and not self.initial_data.get('quiet_hours_end'):
            raise serializers.ValidationError("Quiet hours end time is required when start time is set")
        return value
    
    def validate_quiet_hours_end(self, value):
        """Validate quiet hours end time"""
        if value and not self.initial_data.get('quiet_hours_start'):
            raise serializers.ValidationError("Quiet hours start time is required when end time is set")
        return value


class BulkNotificationSerializer(serializers.Serializer):
    """
    Serializer for bulk notification operations
    """
    user_ids = serializers.ListField(
        child=serializers.IntegerField(),
        min_length=1,
        max_length=1000
    )
    notification_type = serializers.ChoiceField(
        choices=NotificationTemplate.TYPE_CHOICES
    )
    title = serializers.CharField(max_length=200)
    body = serializers.CharField()
    channel = serializers.ChoiceField(
        choices=NotificationTemplate.CHANNEL_CHOICES,
        default='websocket'
    )
    data = serializers.JSONField(required=False, default=dict)
    priority = serializers.ChoiceField(
        choices=Notification.PRIORITY_CHOICES,
        default='medium'
    )
    scheduled_at = serializers.DateTimeField(required=False)
    
    def validate_user_ids(self, value):
        """Validate all user IDs exist"""
        existing_users = User.objects.filter(id__in=value).values_list('id', flat=True)
        missing_ids = set(value) - set(existing_users)
        
        if missing_ids:
            raise serializers.ValidationError(f"Users not found: {list(missing_ids)}")
        
        return value

