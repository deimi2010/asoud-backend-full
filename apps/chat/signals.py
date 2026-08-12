"""
Signals for Chat and Support System
"""

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
import logging

from .models import ChatMessage, ChatRoom, SupportTicket

logger = logging.getLogger(__name__)


@receiver(post_save, sender=ChatMessage)
def update_room_last_message(sender, instance, created, **kwargs):
    """Update room last message timestamp when new message is created"""
    if created:
        try:
            room = instance.chat_room
            room.last_message_at = instance.sent_at
            room.update_last_activity()
            room.save(update_fields=['last_message_at', 'last_activity_at'])
            
            logger.info(f"Updated last message timestamp for room {room.id}")
        except Exception as e:
            logger.error(f"Error updating room last message: {e}")


@receiver(post_save, sender=SupportTicket)
def create_support_chat_room(sender, instance, created, **kwargs):
    """Create chat room for support ticket"""
    if created and not instance.chat_room_id:
        try:
            from .services import ChatService
            chat_service = ChatService()
            
            # Create support chat room
            room = chat_service.create_chat_room(
                name=f"Support Ticket - {instance.subject}",
                room_type=ChatRoom.SUPPORT,
                description=instance.description,
                created_by=instance.user
            )
            
            # Link ticket to room
            instance.chat_room = room
            instance.save(update_fields=['chat_room'])
            
            logger.info(f"Created support chat room {room.id} for ticket {instance.ticket_number}")
        except Exception as e:
            logger.error(f"Error creating support chat room: {e}")


@receiver(post_save, sender=SupportTicket)
def update_ticket_activity(sender, instance, **kwargs):
    """Update ticket last activity timestamp"""
    try:
        # Only update if not already updating to prevent recursion
        if not hasattr(instance, '_updating_activity'):
            instance._updating_activity = True
            instance.update_activity()
            delattr(instance, '_updating_activity')
            logger.debug(f"Updated activity timestamp for ticket {instance.ticket_number}")
    except Exception as e:
        logger.error(f"Error updating ticket activity: {e}")
