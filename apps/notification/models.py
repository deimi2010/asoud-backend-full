"""
Advanced Notification Models for ASOUD Platform
Comprehensive notification system with multiple channels
"""

from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from apps.base.models import BaseModel
import uuid

User = get_user_model()


class NotificationTemplate(BaseModel):
    """
    Template for different types of notifications
    """
    PUSH = 'push'
    EMAIL = 'email'
    SMS = 'sms'
    WEBSOCKET = 'websocket'
    
    CHANNEL_CHOICES = [
        (PUSH, _('Push Notification')),
        (EMAIL, _('Email')),
        (SMS, _('SMS')),
        (WEBSOCKET, _('WebSocket')),
    ]
    
    ORDER_CONFIRMED = 'order_confirmed'
    PAYMENT_SUCCESS = 'payment_success'
    NEW_MESSAGE = 'new_message'
    MARKET_APPROVED = 'market_approved'
    PRODUCT_PUBLISHED = 'product_published'
    DISCOUNT_AVAILABLE = 'discount_available'
    SYSTEM_MAINTENANCE = 'system_maintenance'
    SECURITY_ALERT = 'security_alert'
    
    TYPE_CHOICES = [
        (ORDER_CONFIRMED, _('Order Confirmed')),
        (PAYMENT_SUCCESS, _('Payment Success')),
        (NEW_MESSAGE, _('New Message')),
        (MARKET_APPROVED, _('Market Approved')),
        (PRODUCT_PUBLISHED, _('Product Published')),
        (DISCOUNT_AVAILABLE, _('Discount Available')),
        (SYSTEM_MAINTENANCE, _('System Maintenance')),
        (SECURITY_ALERT, _('Security Alert')),
    ]
    
    name = models.CharField(
        max_length=100,
        verbose_name=_('Template Name'),
        unique=True
    )
    
    notification_type = models.CharField(
        max_length=50,
        choices=TYPE_CHOICES,
        verbose_name=_('Notification Type')
    )
    
    channel = models.CharField(
        max_length=20,
        choices=CHANNEL_CHOICES,
        verbose_name=_('Channel')
    )
    
    subject = models.CharField(
        max_length=200,
        verbose_name=_('Subject'),
        help_text=_('Subject line for email notifications')
    )
    
    title = models.CharField(
        max_length=200,
        verbose_name=_('Title'),
        help_text=_('Title for push notifications')
    )
    
    body = models.TextField(
        verbose_name=_('Body'),
        help_text=_('Main content of the notification')
    )
    
    is_active = models.BooleanField(
        default=True,
        verbose_name=_('Is Active')
    )
    
    variables = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_('Template Variables'),
        help_text=_('Available variables for template rendering')
    )
    
    class Meta:
        verbose_name = _('Notification Template')
        verbose_name_plural = _('Notification Templates')
        unique_together = ['notification_type', 'channel']
        ordering = ['notification_type', 'channel']
    
    def __str__(self):
        return f"{self.get_notification_type_display()} - {self.get_channel_display()}"


class NotificationPreference(BaseModel):
    """
    User notification preferences
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='notification_preferences',
        verbose_name=_('User')
    )
    
    # Push notification preferences
    push_enabled = models.BooleanField(
        default=True,
        verbose_name=_('Push Notifications Enabled')
    )
    
    push_orders = models.BooleanField(
        default=True,
        verbose_name=_('Order Notifications')
    )
    
    push_messages = models.BooleanField(
        default=True,
        verbose_name=_('Message Notifications')
    )
    
    push_marketing = models.BooleanField(
        default=True,
        verbose_name=_('Marketing Notifications')
    )
    
    push_system = models.BooleanField(
        default=True,
        verbose_name=_('System Notifications')
    )
    
    # Email preferences
    email_enabled = models.BooleanField(
        default=True,
        verbose_name=_('Email Notifications Enabled')
    )
    
    email_orders = models.BooleanField(
        default=True,
        verbose_name=_('Order Emails')
    )
    
    email_messages = models.BooleanField(
        default=False,
        verbose_name=_('Message Emails')
    )
    
    email_marketing = models.BooleanField(
        default=True,
        verbose_name=_('Marketing Emails')
    )
    
    email_system = models.BooleanField(
        default=True,
        verbose_name=_('System Emails')
    )
    
    # SMS preferences
    sms_enabled = models.BooleanField(
        default=False,
        verbose_name=_('SMS Notifications Enabled')
    )
    
    sms_orders = models.BooleanField(
        default=True,
        verbose_name=_('Order SMS')
    )
    
    sms_messages = models.BooleanField(
        default=False,
        verbose_name=_('Message SMS')
    )
    
    sms_marketing = models.BooleanField(
        default=False,
        verbose_name=_('Marketing SMS')
    )
    
    sms_system = models.BooleanField(
        default=True,
        verbose_name=_('System SMS')
    )
    
    # Timing preferences
    quiet_hours_start = models.TimeField(
        null=True,
        blank=True,
        verbose_name=_('Quiet Hours Start')
    )
    
    quiet_hours_end = models.TimeField(
        null=True,
        blank=True,
        verbose_name=_('Quiet Hours End')
    )
    
    timezone = models.CharField(
        max_length=50,
        default='UTC',
        verbose_name=_('Timezone')
    )
    
    class Meta:
        verbose_name = _('Notification Preference')
        verbose_name_plural = _('Notification Preferences')
    
    def __str__(self):
        return f"Preferences for {self.user.username}"


class Notification(BaseModel):
    """
    Individual notification record
    """
    PENDING = 'pending'
    SENT = 'sent'
    DELIVERED = 'delivered'
    FAILED = 'failed'
    READ = 'read'
    
    STATUS_CHOICES = [
        (PENDING, _('Pending')),
        (SENT, _('Sent')),
        (DELIVERED, _('Delivered')),
        (FAILED, _('Failed')),
        (READ, _('Read')),
    ]
    
    HIGH = 'high'
    MEDIUM = 'medium'
    LOW = 'low'
    
    PRIORITY_CHOICES = [
        (HIGH, _('High')),
        (MEDIUM, _('Medium')),
        (LOW, _('Low')),
    ]
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name=_('User')
    )
    
    template = models.ForeignKey(
        NotificationTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_('Template')
    )
    
    notification_type = models.CharField(
        max_length=50,
        choices=NotificationTemplate.TYPE_CHOICES,
        verbose_name=_('Notification Type')
    )
    
    channel = models.CharField(
        max_length=20,
        choices=NotificationTemplate.CHANNEL_CHOICES,
        verbose_name=_('Channel')
    )
    
    title = models.CharField(
        max_length=200,
        verbose_name=_('Title')
    )
    
    body = models.TextField(
        verbose_name=_('Body')
    )
    
    data = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_('Additional Data')
    )
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=PENDING,
        verbose_name=_('Status')
    )
    
    priority = models.CharField(
        max_length=10,
        choices=PRIORITY_CHOICES,
        default=MEDIUM,
        verbose_name=_('Priority')
    )
    
    scheduled_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Scheduled At')
    )
    
    sent_at = models.DateTimeField(
        null=True,
        blank=True,
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
    
    failure_reason = models.TextField(
        null=True,
        blank=True,
        verbose_name=_('Failure Reason')
    )
    
    retry_count = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Retry Count')
    )
    
    max_retries = models.PositiveIntegerField(
        default=3,
        verbose_name=_('Max Retries')
    )
    
    # Related object
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
    
    class Meta:
        verbose_name = _('Notification')
        verbose_name_plural = _('Notifications')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['channel', 'status']),
            models.Index(fields=['notification_type', 'status']),
            models.Index(fields=['scheduled_at']),
        ]
    
    def __str__(self):
        return f"{self.get_channel_display()} - {self.title} - {self.user.username}"
    
    def mark_as_sent(self):
        """Mark notification as sent"""
        self.status = self.SENT
        self.sent_at = timezone.now()
        self.save(update_fields=['status', 'sent_at'])
    
    def mark_as_delivered(self):
        """Mark notification as delivered"""
        self.status = self.DELIVERED
        self.delivered_at = timezone.now()
        self.save(update_fields=['status', 'delivered_at'])
    
    def mark_as_read(self):
        """Mark notification as read"""
        self.status = self.READ
        self.read_at = timezone.now()
        self.save(update_fields=['status', 'read_at'])
    
    def mark_as_failed(self, reason=None):
        """Mark notification as failed"""
        self.status = self.FAILED
        if reason:
            self.failure_reason = reason
        self.save(update_fields=['status', 'failure_reason'])
    
    def can_retry(self):
        """Check if notification can be retried"""
        return self.retry_count < self.max_retries and self.status == self.FAILED
    
    def increment_retry(self):
        """Increment retry count"""
        self.retry_count += 1
        self.save(update_fields=['retry_count'])


class NotificationLog(BaseModel):
    """
    Log of notification delivery attempts
    """
    notification = models.ForeignKey(
        Notification,
        on_delete=models.CASCADE,
        related_name='logs',
        verbose_name=_('Notification')
    )
    
    attempt_number = models.PositiveIntegerField(
        verbose_name=_('Attempt Number')
    )
    
    status = models.CharField(
        max_length=20,
        choices=Notification.STATUS_CHOICES,
        verbose_name=_('Status')
    )
    
    response_data = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_('Response Data')
    )
    
    error_message = models.TextField(
        null=True,
        blank=True,
        verbose_name=_('Error Message')
    )
    
    duration_ms = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name=_('Duration (ms)')
    )
    
    class Meta:
        verbose_name = _('Notification Log')
        verbose_name_plural = _('Notification Logs')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Log for {self.notification} - Attempt {self.attempt_number}"


class NotificationQueue(BaseModel):
    """
    Queue for managing notification delivery
    """
    notification = models.OneToOneField(
        Notification,
        on_delete=models.CASCADE,
        related_name='queue_entry',
        verbose_name=_('Notification')
    )
    
    priority = models.PositiveIntegerField(
        default=0,
        verbose_name=_('Queue Priority'),
        help_text=_('Higher number = higher priority')
    )
    
    scheduled_at = models.DateTimeField(
        verbose_name=_('Scheduled At')
    )
    
    is_processing = models.BooleanField(
        default=False,
        verbose_name=_('Is Processing')
    )
    
    processing_started_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Processing Started At')
    )
    
    class Meta:
        verbose_name = _('Notification Queue')
        verbose_name_plural = _('Notification Queues')
        ordering = ['-priority', 'scheduled_at']
        indexes = [
            models.Index(fields=['scheduled_at', 'is_processing']),
            models.Index(fields=['priority', 'scheduled_at']),
        ]
    
    def __str__(self):
        return f"Queue entry for {self.notification}"
    
    def mark_as_processing(self):
        """Mark queue entry as processing"""
        self.is_processing = True
        self.processing_started_at = timezone.now()
        self.save(update_fields=['is_processing', 'processing_started_at'])
    
    def mark_as_completed(self):
        """Mark queue entry as completed"""
        self.delete()
