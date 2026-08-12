"""
Advanced Chat and Support Views for ASOUD Platform
API views for chat rooms, messages, and support tickets
"""

import logging
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import PermissionDenied
from apps.core.rate_limit import AtomicRateThrottle
from apps.core.base_views import BaseAPIView
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db.models import Q, Count, Avg, Max
from django.core.cache import cache
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.core.paginator import Paginator

from .models import (
    ChatRoom, ChatParticipant, ChatMessage, ChatMessageRead,
    SupportTicket, ChatAnalytics, chat_user_display_name
)
from .serializers import (
    ChatRoomSerializer, ChatParticipantSerializer, ChatMessageSerializer,
    SupportTicketSerializer, ChatAnalyticsSerializer, ChatRoomCreateSerializer,
    ChatMessageCreateSerializer, SupportTicketCreateSerializer,
    SupportTicketUpdateSerializer, ChatRoomUpdateSerializer
)
from .services import (
    ChatService, ChatMembershipError, SupportService, ChatAnalyticsService,
)

User = get_user_model()
logger = logging.getLogger(__name__)


class ChatRoomViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing chat rooms
    """
    serializer_class = ChatRoomSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_throttles(self):
        if self.action in ('participants', 'add_participant') and self.request.method == 'POST':
            self.throttle_scope = 'chat_member_add'
            return [AtomicRateThrottle()]
        return super().get_throttles()

    @staticmethod
    def _membership_error(exc):
        return Response(
            {'error': exc.message, 'code': exc.code},
            status=exc.http_status,
        )
    
    def get_queryset(self):
        """Get chat rooms for current user"""
        return ChatRoom.objects.filter(
            participants=self.request.user
        ).prefetch_related('participants', 'messages').order_by('-last_message_at')
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'create':
            return ChatRoomCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return ChatRoomUpdateSerializer
        return ChatRoomSerializer
    
    def perform_create(self, serializer):
        """Create chat room with participants"""
        try:
            chat_service = ChatService()
            participants = serializer.validated_data.get('participants', [])
            
            # Create room
            room = chat_service.create_chat_room(
                name=serializer.validated_data.get('name', 'Chat Room'),
                room_type=serializer.validated_data.get('room_type', ChatRoom.PRIVATE),
                description=serializer.validated_data.get('description', ''),
                created_by=self.request.user,
                participants=participants,
                max_participants=serializer.validated_data.get('max_participants', 100),
                is_encrypted=serializer.validated_data.get('is_encrypted', False),
                allow_file_sharing=serializer.validated_data.get('allow_file_sharing', True),
            )
            
            serializer.instance = room
            
        except Exception as e:
            logger.error(f"Error creating chat room: {e}")
            raise

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            self.perform_create(serializer)
        except ChatMembershipError as exc:
            return self._membership_error(exc)
        output = ChatRoomSerializer(serializer.instance, context={'request': request})
        return Response(output.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        room = self.get_object()
        if room.room_type != ChatRoom.GROUP:
            return Response(
                {'error': 'Room settings are system-managed.', 'code': 'room_system_managed'},
                status=status.HTTP_409_CONFLICT,
            )
        membership = ChatParticipant.objects.filter(chat_room=room, user=request.user).first()
        if not membership:
            raise PermissionDenied()
        requested_fields = set(request.data.keys())
        metadata_fields = {'name', 'description'}
        sensitive_fields = {'is_encrypted', 'allow_file_sharing', 'max_participants'}
        unsupported = requested_fields - metadata_fields - sensitive_fields
        if unsupported:
            return Response(
                {'error': 'Unsupported room fields.', 'code': 'unsupported_room_fields', 'fields': sorted(unsupported)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if membership.role not in (ChatParticipant.OWNER, ChatParticipant.ADMIN):
            raise PermissionDenied('You cannot update this room.')
        if requested_fields & sensitive_fields and membership.role != ChatParticipant.OWNER:
            raise PermissionDenied('Only the owner may update sensitive room settings.')
        serializer = self.get_serializer(room, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(ChatRoomSerializer(room, context={'request': request}).data)

    def destroy(self, request, *args, **kwargs):
        room = self.get_object()
        try:
            ChatService().archive_group(room, request.user)
        except ChatMembershipError as exc:
            return self._membership_error(exc)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'])
    def add_participant(self, request, pk=None):
        """Add participant to chat room"""
        room = self.get_object()
        user = self._resolve_participant_user(request.data)
        if isinstance(user, Response):
            return user
        role = request.data.get('role', ChatParticipant.MEMBER)
        try:
            membership = ChatService().add_group_participant(room, user, request.user, role)
        except ChatMembershipError as exc:
            return self._membership_error(exc)
        return Response(
            ChatParticipantSerializer(membership).data,
            status=status.HTTP_201_CREATED,
        )
    
    @action(detail=True, methods=['post'])
    def remove_participant(self, request, pk=None):
        """Remove participant from chat room"""
        try:
            room = self.get_object()
            user = self._resolve_participant_user(request.data)
            if isinstance(user, Response):
                return user
            chat_service = ChatService()
            
            success = chat_service.remove_participant(
                room, user, request.user
            )
            
            if success:
                return Response({
                    'message': 'Participant removed successfully'
                })
            else:
                return Response(
                    {'error': 'Failed to remove participant'},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except ChatMembershipError as exc:
            return self._membership_error(exc)
        except Exception as e:
            logger.error(f"Error removing participant: {e}")
            return Response(
                {'error': 'Internal server error'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get', 'post'])
    def participants(self, request, pk=None):
        """Get chat room participants"""
        try:
            room = self.get_object()
            if request.method == 'POST':
                user = self._resolve_participant_user(request.data)
                if isinstance(user, Response):
                    return user
                role = request.data.get('role', ChatParticipant.MEMBER)
                try:
                    membership = ChatService().add_group_participant(
                        room, user, request.user, role,
                    )
                except ChatMembershipError as exc:
                    return self._membership_error(exc)
                return Response(
                    ChatParticipantSerializer(membership).data,
                    status=status.HTTP_201_CREATED,
                )
            participants = ChatParticipant.objects.filter(
                chat_room=room
            ).select_related('user').order_by('id')
            
            serializer = ChatParticipantSerializer(participants, many=True)
            return Response(serializer.data)
            
        except Exception as e:
            logger.error(f"Error getting participants: {e}")
            return Response(
                {'error': 'Internal server error'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get'])
    def analytics(self, request, pk=None):
        """Get chat room analytics"""
        if not getattr(settings, 'ANALYTICS_ENABLED', False):
            return Response(
                {'error': 'Analytics is disabled'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        try:
            room = self.get_object()
            analytics_service = ChatAnalyticsService()
            analytics_data = analytics_service.get_room_analytics(room)
            return Response(analytics_data)
        except Exception as e:
            logger.error(f"Error getting analytics: {e}")
            return Response(
                {'error': 'Internal server error'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(
        detail=True,
        methods=['patch', 'delete'],
        url_path=r'participants/(?P<user_id>[^/.]+)',
    )
    def participant(self, request, pk=None, user_id=None):
        room = self.get_object()
        try:
            user = User.objects.get(pk=user_id)
        except (User.DoesNotExist, ValueError):
            return Response(
                {'error': 'Participant not found.', 'code': 'participant_not_found'},
                status=status.HTTP_404_NOT_FOUND,
            )
        service = ChatService()
        try:
            if request.method == 'PATCH':
                membership = service.change_group_role(
                    room, user, request.user, request.data.get('role'),
                )
                return Response(ChatParticipantSerializer(membership).data)
            service.remove_group_participant(room, user, request.user)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ChatMembershipError as exc:
            return self._membership_error(exc)

    @action(detail=True, methods=['post'])
    def leave(self, request, pk=None):
        room = self.get_object()
        try:
            room = ChatService().leave_group(room, request.user)
        except ChatMembershipError as exc:
            return self._membership_error(exc)
        return Response({'status': room.status})

    @action(detail=True, methods=['post'], url_path='transfer-ownership')
    def transfer_ownership(self, request, pk=None):
        room = self.get_object()
        user_id = request.data.get('user_id')
        try:
            user = User.objects.get(pk=user_id)
        except (User.DoesNotExist, ValueError, TypeError):
            return Response(
                {'error': 'Participant not found.', 'code': 'participant_not_found'},
                status=status.HTTP_404_NOT_FOUND,
            )
        try:
            membership = ChatService().transfer_group_ownership(room, user, request.user)
        except ChatMembershipError as exc:
            return self._membership_error(exc)
        return Response(ChatParticipantSerializer(membership).data)

    @staticmethod
    def _resolve_participant_user(data):
        mobile_number = data.get('mobile_number')
        user_id = data.get('user_id')
        if not mobile_number and not user_id:
            return Response(
                {'error': 'mobile_number is required.', 'code': 'mobile_number_required'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            if mobile_number:
                return User.objects.get(mobile_number=mobile_number)
            return User.objects.get(pk=user_id)
        except (User.DoesNotExist, ValueError, TypeError):
            return Response(
                {'error': 'No matching user was found.', 'code': 'participant_not_found'},
                status=status.HTTP_404_NOT_FOUND,
            )


class ChatMessageViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing chat messages
    """
    serializer_class = ChatMessageSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Get messages for current user's chat rooms"""
        user_rooms = ChatRoom.objects.filter(
            participants=self.request.user
        )
        return ChatMessage.objects.filter(
            chat_room__in=user_rooms,
            is_deleted=False
        ).select_related('sender', 'chat_room', 'reply_to').order_by('-sent_at')
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'create':
            return ChatMessageCreateSerializer
        return ChatMessageSerializer
    
    def perform_create(self, serializer):
        """Create chat message"""
        try:
            chat_service = ChatService()
            room_id = self.request.data.get('chat_room_id')
            
            if not room_id:
                raise ValueError("chat_room_id is required")
            
            room = ChatRoom.objects.get(id=room_id)
            
            # Check if user is participant
            if not room.is_participant(self.request.user):
                raise PermissionDenied("User is not a participant in this chat room")
            
            message = chat_service.send_message(
                chat_room=room,
                sender=self.request.user,
                content=serializer.validated_data['content'],
                message_type=serializer.validated_data.get('message_type', ChatMessage.TEXT),
                file=self.request.FILES.get('file'),
                reply_to=serializer.validated_data.get('reply_to')
            )
            
            serializer.instance = message
            
        except Exception as e:
            logger.error(f"Error creating message: {e}")
            raise
    
    @action(detail=True, methods=['post'])
    def mark_as_read(self, request, pk=None):
        """Mark message as read"""
        try:
            message = self.get_object()
            chat_service = ChatService()
            
            success = chat_service.mark_message_as_read(message, request.user)
            
            if success:
                return Response({
                    'message': 'Message marked as read',
                    'status': message.status
                })
            else:
                return Response(
                    {'error': 'Failed to mark message as read'},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
        except Exception as e:
            logger.error(f"Error marking message as read: {e}")
            return Response(
                {'error': 'Internal server error'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def edit(self, request, pk=None):
        """Edit message content"""
        try:
            message = self.get_object()
            new_content = request.data.get('content', '').strip()
            
            if not new_content:
                return Response(
                    {'error': 'Content is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Check if user is the sender
            if message.sender != request.user:
                return Response(
                    {'error': 'You can only edit your own messages'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Edit message
            message.edit_message(new_content)
            
            return Response({
                'message': 'Message edited successfully',
                'content': message.content,
                'edited_at': message.edited_at
            })
            
        except Exception as e:
            logger.error(f"Error editing message: {e}")
            return Response(
                {'error': 'Internal server error'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def delete(self, request, pk=None):
        """Delete message (soft delete)"""
        try:
            message = self.get_object()
            
            # The current participant schema has no room-management permission.
            # Message deletion therefore remains sender-only.
            if message.sender != request.user:
                return Response(
                    {'error': 'You are not authorized to delete this message'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Delete message
            message.delete_message()
            
            return Response({
                'message': 'Message deleted successfully'
            })
            
        except Exception as e:
            logger.error(f"Error deleting message: {e}")
            return Response(
                {'error': 'Internal server error'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def room_messages(self, request):
        """Get messages for a specific chat room"""
        try:
            room_id = request.query_params.get('room_id')
            if not room_id:
                return Response(
                    {'error': 'room_id is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            room = ChatRoom.objects.get(id=room_id)
            
            # Check if user is participant
            if not room.is_participant(request.user):
                return Response(
                    {'error': 'User is not a participant in this chat room'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Get pagination parameters
            page = int(request.query_params.get('page', 1))
            page_size = int(request.query_params.get('page_size', 50))
            message_type = request.query_params.get('message_type')
            
            # Get messages
            chat_service = ChatService()
            messages = chat_service.get_messages(
                room, request.user, 
                limit=page_size,
                offset=(page - 1) * page_size,
                message_type=message_type
            )
            
            # Paginate results
            paginator = Paginator(messages, page_size)
            page_obj = paginator.get_page(page)
            
            serializer = ChatMessageSerializer(page_obj.object_list, many=True)
            
            return Response({
                'results': serializer.data,
                'count': paginator.count,
                'page': page,
                'page_size': page_size,
                'total_pages': paginator.num_pages,
                'has_next': page_obj.has_next(),
                'has_previous': page_obj.has_previous(),
            })
            
        except ChatRoom.DoesNotExist:
            return Response(
                {'error': 'Chat room not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error getting room messages: {e}")
            return Response(
                {'error': 'Internal server error'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class SupportTicketViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing support tickets
    """
    serializer_class = SupportTicketSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Get support tickets for current user"""
        if self.request.user.is_staff:
            return SupportTicket.objects.all().prefetch_related(
                'user', 'assigned_to', 'chat_room'
            ).order_by('-opened_at')
        else:
            return SupportTicket.objects.filter(
                user=self.request.user
            ).prefetch_related(
                'user', 'assigned_to', 'chat_room'
            ).order_by('-opened_at')
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'create':
            return SupportTicketCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return SupportTicketUpdateSerializer
        return SupportTicketSerializer
    
    def perform_create(self, serializer):
        """Create support ticket"""
        try:
            support_service = SupportService()
            
            ticket = support_service.create_support_ticket(
                user=self.request.user,
                subject=serializer.validated_data['subject'],
                description=serializer.validated_data['description'],
                category=serializer.validated_data.get('category', SupportTicket.GENERAL),
                priority=serializer.validated_data.get('priority', SupportTicket.MEDIUM)
            )
            
            serializer.instance = ticket
            
        except Exception as e:
            logger.error(f"Error creating support ticket: {e}")
            raise
    
    @action(detail=True, methods=['post'])
    def assign(self, request, pk=None):
        """Assign ticket to agent"""
        try:
            ticket = self.get_object()
            agent_id = request.data.get('agent_id')
            
            if not agent_id:
                return Response(
                    {'error': 'agent_id is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if not request.user.is_staff:
                return Response(
                    {'error': 'Only staff members can assign tickets'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            agent = User.objects.get(id=agent_id)
            support_service = SupportService()
            
            success = support_service.assign_ticket(
                ticket, agent, request.user
            )
            
            if success:
                return Response({
                    'message': 'Ticket assigned successfully',
                    'assigned_to': {
                        'id': agent.id,
                        'username': chat_user_display_name(agent)
                    }
                })
            else:
                return Response(
                    {'error': 'Failed to assign ticket'},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
        except User.DoesNotExist:
            return Response(
                {'error': 'Agent not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error assigning ticket: {e}")
            return Response(
                {'error': 'Internal server error'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        """Resolve ticket"""
        try:
            ticket = self.get_object()
            resolution = request.data.get('resolution', '')
            
            if not resolution:
                return Response(
                    {'error': 'Resolution is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            support_service = SupportService()
            
            success = support_service.resolve_ticket(
                ticket, resolution, request.user
            )
            
            if success:
                return Response({
                    'message': 'Ticket resolved successfully',
                    'resolution': resolution,
                    'resolved_at': ticket.resolved_at
                })
            else:
                return Response(
                    {'error': 'Failed to resolve ticket'},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
        except Exception as e:
            logger.error(f"Error resolving ticket: {e}")
            return Response(
                {'error': 'Internal server error'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def close(self, request, pk=None):
        """Close ticket"""
        try:
            ticket = self.get_object()
            
            if not request.user.is_staff and ticket.assigned_to != request.user:
                return Response(
                    {'error': 'You are not authorized to close this ticket'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            ticket.close()
            
            return Response({
                'message': 'Ticket closed successfully',
                'closed_at': ticket.closed_at
            })
            
        except Exception as e:
            logger.error(f"Error closing ticket: {e}")
            return Response(
                {'error': 'Internal server error'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get support ticket statistics"""
        try:
            support_service = SupportService()
            stats = support_service.get_ticket_stats(request.user)
            
            return Response(stats)
            
        except Exception as e:
            logger.error(f"Error getting ticket stats: {e}")
            return Response(
                {'error': 'Internal server error'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ChatAnalyticsView(BaseAPIView):
    """
    View for chat analytics
    """
    permission_classes = [permissions.IsAuthenticated]
    
    @method_decorator(cache_page(60 * 5))  # Cache for 5 minutes
    def get(self, request):
        """Get chat analytics"""
        if not getattr(settings, 'ANALYTICS_ENABLED', False):
            return self.error_response('Analytics is disabled', 503)
        try:
            analytics_service = ChatAnalyticsService()
            
            # Get global analytics
            global_analytics = analytics_service.get_global_analytics()
            
            # Get user-specific analytics
            user_rooms = ChatRoom.objects.filter(
                participants=request.user
            )
            
            user_analytics = {
                'user_rooms_count': user_rooms.count(),
                'active_rooms': user_rooms.filter(
                    status=ChatRoom.ACTIVE
                ).count(),
                'total_messages': ChatMessage.objects.filter(
                    chat_room__in=user_rooms,
                    is_deleted=False
                ).count(),
                'unread_messages': sum(
                    ChatService().get_unread_count(room, request.user)
                    for room in user_rooms
                ),
            }
            
            return self.success_response(data={
                'global': global_analytics,
                'user': user_analytics,
                'generated_at': timezone.now()
            })
            
        except Exception as e:
            logger.error(f"Error getting chat analytics: {e}")
            return self.error_response(f"Internal server error: {str(e)}", 500)


class ChatSearchView(BaseAPIView):
    """
    View for searching chat messages
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        """Search chat messages"""
        try:
            query = request.query_params.get('q', '').strip()
            room_id = request.query_params.get('room_id')
            message_type = request.query_params.get('message_type')
            
            if not query:
                return self.error_response("Query parameter is required", 400)
            
            # Build search query
            search_query = Q(
                content__icontains=query,
                is_deleted=False
            )
            
            # Filter by room if specified
            if room_id:
                try:
                    room = ChatRoom.objects.get(id=room_id)
                    if not room.is_participant(request.user):
                        return self.error_response("User is not a participant in this chat room", 403)
                    search_query &= Q(chat_room=room)
                except ChatRoom.DoesNotExist:
                    return self.error_response("Chat room not found", 404)
            else:
                # Search only in user's rooms
                user_rooms = ChatRoom.objects.filter(
                    participants=request.user
                )
                search_query &= Q(chat_room__in=user_rooms)
            
            # Filter by message type if specified
            if message_type:
                search_query &= Q(message_type=message_type)
            
            # Get pagination parameters
            page = int(request.query_params.get('page', 1))
            page_size = int(request.query_params.get('page_size', 20))
            
            # Search messages
            messages = ChatMessage.objects.filter(search_query).select_related(
                'sender', 'chat_room'
            ).order_by('-sent_at')
            
            # Paginate results
            paginator = Paginator(messages, page_size)
            page_obj = paginator.get_page(page)
            
            serializer = ChatMessageSerializer(page_obj.object_list, many=True)
            
            return self.success_response(data={
                'results': serializer.data,
                'count': paginator.count,
                'page': page,
                'page_size': page_size,
                'total_pages': paginator.num_pages,
                'has_next': page_obj.has_next(),
                'has_previous': page_obj.has_previous(),
                'query': query,
            })
            
        except ChatRoom.DoesNotExist:
            return self.error_response("Chat room not found", 404)
        except Exception as e:
            logger.error(f"Error searching messages: {e}")
            return self.error_response(f"Internal server error: {str(e)}", 500)
