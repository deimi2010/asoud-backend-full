"""
Advanced Chat and Support Admin for ASOUD Platform
Admin interface for chat rooms, messages, and support tickets
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from django.db.models import Count, Q

from .models import (
    ChatRoom, ChatParticipant, ChatMembershipEvent, ChatMessage, ChatMessageRead,
    SupportTicket, ChatAnalytics
)


@admin.register(ChatRoom)
class ChatRoomAdmin(admin.ModelAdmin):
    """Admin interface for chat rooms"""
    list_display = [
        'name', 'room_type', 'status', 'created_by', 'participant_count',
        'last_message_at', 'created_at'
    ]
    list_filter = ['room_type', 'status', 'created_at']
    search_fields = ['name', 'description', 'created_by__mobile_number']
    readonly_fields = ['id', 'created_at', 'last_message_at', 'participant_count']
    date_hierarchy = 'created_at'
    ordering = ['-last_message_at']
    
    def participant_count(self, obj):
        return obj.get_participant_count()
    participant_count.short_description = 'Participants'


@admin.register(ChatParticipant)
class ChatParticipantAdmin(admin.ModelAdmin):
    """Admin interface for chat participants"""
    list_display = [
        'user', 'chat_room', 'role', 'joined_at'
    ]
    list_filter = ['role', 'chat_room__room_type']
    search_fields = ['user__mobile_number', 'chat_room__name']


@admin.register(ChatMembershipEvent)
class ChatMembershipEventAdmin(admin.ModelAdmin):
    list_display = ['chat_room', 'action', 'actor', 'subject', 'old_role', 'new_role', 'created_at']
    list_filter = ['action', 'old_role', 'new_role']
    readonly_fields = [
        'chat_room', 'action', 'actor', 'subject', 'old_role', 'new_role', 'created_at',
    ]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    """Admin interface for chat messages"""
    list_display = [
        'id', 'sender', 'chat_room', 'message_type', 'content_preview',
        'status', 'sent_at', 'is_edited', 'is_deleted'
    ]
    list_filter = ['message_type', 'status', 'is_edited', 'is_deleted', 'sent_at']
    search_fields = ['content', 'sender__mobile_number', 'chat_room__name']
    readonly_fields = ['id', 'sent_at', 'delivered_at', 'read_at']
    date_hierarchy = 'sent_at'
    ordering = ['-sent_at']
    
    def content_preview(self, obj):
        content = obj.content
        if len(content) > 50:
            content = content[:50] + '...'
        if obj.is_edited:
            content += ' [EDITED]'
        return content
    content_preview.short_description = 'Content'


@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    """Admin interface for support tickets"""
    list_display = [
        'ticket_number', 'subject', 'user', 'assigned_to', 'category',
        'priority', 'status', 'opened_at', 'satisfaction_rating'
    ]
    list_filter = ['category', 'priority', 'status', 'opened_at']
    search_fields = ['ticket_number', 'subject', 'user__mobile_number']
    readonly_fields = ['id', 'ticket_number', 'opened_at', 'resolved_at', 'closed_at']
    date_hierarchy = 'opened_at'
    ordering = ['-opened_at']


@admin.register(ChatAnalytics)
class ChatAnalyticsAdmin(admin.ModelAdmin):
    """Admin interface for chat analytics"""
    list_display = [
        'chat_room', 'total_messages', 'messages_today',
        'active_participants', 'files_shared', 'last_calculated_at'
    ]
    list_filter = ['last_calculated_at']
    search_fields = ['chat_room__name']
    readonly_fields = ['last_calculated_at']
    ordering = ['-last_calculated_at']
