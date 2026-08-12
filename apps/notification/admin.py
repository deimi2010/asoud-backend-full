"""
Admin interface for notification models
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from .models import (
    Notification, NotificationTemplate, NotificationPreference,
    NotificationLog, NotificationQueue
)


@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'notification_type', 'channel', 'is_active', 'created_at'
    ]
    list_filter = ['notification_type', 'channel', 'is_active', 'created_at']
    search_fields = ['name', 'title', 'body']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'notification_type', 'channel', 'is_active')
        }),
        ('Content', {
            'fields': ('subject', 'title', 'body')
        }),
        ('Variables', {
            'fields': ('variables',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'push_enabled', 'email_enabled', 'sms_enabled', 'timezone'
    ]
    list_filter = [
        'push_enabled', 'email_enabled', 'sms_enabled',
        'push_orders', 'email_orders', 'sms_orders',
        'timezone'
    ]
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('User', {
            'fields': ('user',)
        }),
        ('Push Notifications', {
            'fields': (
                'push_enabled', 'push_orders', 'push_messages',
                'push_marketing', 'push_system'
            )
        }),
        ('Email Notifications', {
            'fields': (
                'email_enabled', 'email_orders', 'email_messages',
                'email_marketing', 'email_system'
            )
        }),
        ('SMS Notifications', {
            'fields': (
                'sms_enabled', 'sms_orders', 'sms_messages',
                'sms_marketing', 'sms_system'
            )
        }),
        ('Timing Preferences', {
            'fields': ('quiet_hours_start', 'quiet_hours_end', 'timezone')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'user', 'notification_type', 'channel', 'title',
        'status', 'priority', 'created_at', 'sent_at'
    ]
    list_filter = [
        'notification_type', 'channel', 'status', 'priority',
        'created_at', 'sent_at'
    ]
    search_fields = [
        'user__username', 'user__email', 'title', 'body'
    ]
    readonly_fields = [
        'id', 'sent_at', 'delivered_at', 'read_at',
        'failure_reason', 'retry_count', 'created_at', 'updated_at'
    ]
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'user', 'template', 'notification_type', 'channel')
        }),
        ('Content', {
            'fields': ('title', 'body', 'data')
        }),
        ('Status', {
            'fields': ('status', 'priority', 'scheduled_at')
        }),
        ('Timestamps', {
            'fields': ('sent_at', 'delivered_at', 'read_at'),
            'classes': ('collapse',)
        }),
        ('Retry Information', {
            'fields': ('retry_count', 'max_retries', 'failure_reason'),
            'classes': ('collapse',)
        }),
        ('Related Object', {
            'fields': ('content_type', 'object_id'),
            'classes': ('collapse',)
        }),
        ('System Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'template')
    
    actions = ['mark_as_sent', 'mark_as_delivered', 'mark_as_read', 'retry_failed']
    
    def mark_as_sent(self, request, queryset):
        """Mark selected notifications as sent"""
        count = 0
        for notification in queryset:
            if notification.status == Notification.PENDING:
                notification.mark_as_sent()
                count += 1
        
        self.message_user(request, f'{count} notifications marked as sent.')
    mark_as_sent.short_description = "Mark as sent"
    
    def mark_as_delivered(self, request, queryset):
        """Mark selected notifications as delivered"""
        count = 0
        for notification in queryset:
            if notification.status == Notification.SENT:
                notification.mark_as_delivered()
                count += 1
        
        self.message_user(request, f'{count} notifications marked as delivered.')
    mark_as_delivered.short_description = "Mark as delivered"
    
    def mark_as_read(self, request, queryset):
        """Mark selected notifications as read"""
        count = 0
        for notification in queryset:
            if notification.status in [Notification.SENT, Notification.DELIVERED]:
                notification.mark_as_read()
                count += 1
        
        self.message_user(request, f'{count} notifications marked as read.')
    mark_as_read.short_description = "Mark as read"
    
    def retry_failed(self, request, queryset):
        """Retry failed notifications"""
        count = 0
        for notification in queryset:
            if notification.can_retry():
                notification.status = Notification.PENDING
                notification.scheduled_at = timezone.now()
                notification.save()
                count += 1
        
        self.message_user(request, f'{count} failed notifications queued for retry.')
    retry_failed.short_description = "Retry failed notifications"


@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'notification', 'attempt_number', 'status',
        'duration_ms', 'created_at'
    ]
    list_filter = ['status', 'attempt_number', 'created_at']
    search_fields = [
        'notification__user__username', 'notification__title',
        'error_message'
    ]
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('notification', 'attempt_number', 'status')
        }),
        ('Response Data', {
            'fields': ('response_data', 'error_message', 'duration_ms'),
            'classes': ('collapse',)
        }),
        ('Timestamp', {
            'fields': ('created_at',)
        })
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('notification__user')


@admin.register(NotificationQueue)
class NotificationQueueAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'notification', 'priority', 'scheduled_at',
        'is_processing', 'created_at'
    ]
    list_filter = ['is_processing', 'priority', 'scheduled_at', 'created_at']
    search_fields = [
        'notification__user__username', 'notification__title'
    ]
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('Queue Information', {
            'fields': ('notification', 'priority', 'scheduled_at')
        }),
        ('Processing Status', {
            'fields': ('is_processing', 'processing_started_at')
        }),
        ('Timestamp', {
            'fields': ('created_at',)
        })
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('notification__user')
    
    actions = ['process_selected', 'reschedule_immediate']
    
    def process_selected(self, request, queryset):
        """Process selected queue entries"""
        from apps.notification.services import NotificationService
        
        service = NotificationService()
        count = 0
        
        for queue_entry in queryset:
            if not queue_entry.is_processing:
                success = service._process_notification(queue_entry.notification)
                if success:
                    count += 1
        
        self.message_user(request, f'{count} queue entries processed.')
    process_selected.short_description = "Process selected entries"
    
    def reschedule_immediate(self, request, queryset):
        """Reschedule selected entries for immediate processing"""
        count = 0
        for queue_entry in queryset:
            queue_entry.scheduled_at = timezone.now()
            queue_entry.save()
            count += 1
        
        self.message_user(request, f'{count} queue entries rescheduled for immediate processing.')
    reschedule_immediate.short_description = "Reschedule for immediate processing"


# Customize admin site
admin.site.site_header = "ASOUD Notification Administration"
admin.site.site_title = "ASOUD Notifications"
admin.site.index_title = "Notification Management"