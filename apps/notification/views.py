"""
Notification Views for ASOUD Platform
API views for notification management
"""

import logging
from rest_framework import viewsets, status, permissions, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from apps.core.base_views import BaseCreateView
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page

from .models import (
    DeviceInstallation, Notification, NotificationTemplate, NotificationPreference,
    NotificationQueue
)
from .serializers import (
    NotificationSerializer, NotificationTemplateSerializer,
    NotificationPreferenceSerializer, NotificationCreateSerializer,
    NotificationUpdateSerializer, NotificationQueueSerializer, NotificationStatsSerializer,
    NotificationTemplateCreateSerializer, NotificationPreferenceUpdateSerializer,
    BulkNotificationSerializer, DeviceInstallationSerializer
)
from .services import NotificationService, NotificationQueueProcessor

User = get_user_model()


class NotificationCleanupSerializer(serializers.Serializer):
    days = serializers.IntegerField(min_value=1, default=30)


class DeviceInstallationViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = DeviceInstallationSerializer
    http_method_names = ['get', 'post', 'delete', 'head', 'options']
    lookup_value_converter = 'uuid'
    lookup_value_regex = '[0-9a-fA-F-]{36}'

    def get_queryset(self):
        return DeviceInstallation.objects.filter(user=self.request.user).order_by('-last_seen_at')

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save(update_fields=['is_active', 'updated_at'])
logger = logging.getLogger(__name__)


class NotificationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing notifications
    """
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['get', 'post', 'head', 'options']

    def get_permissions(self):
        if self.action == 'create':
            return [permissions.IsAdminUser()]
        return [permission() for permission in self.permission_classes]
    
    def get_queryset(self):
        """Get notifications for current user"""
        return Notification.objects.filter(user=self.request.user)
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'create':
            return NotificationCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return NotificationUpdateSerializer
        return NotificationSerializer
    
    def create(self, request, *args, **kwargs):
        """Create a new notification"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            # Get user
            user = User.objects.get(id=serializer.validated_data['user_id'])
            
            # Send notification
            service = NotificationService()
            success = service.send_notification(
                user=user,
                notification_type=serializer.validated_data['notification_type'],
                title=serializer.validated_data['title'],
                body=serializer.validated_data['body'],
                channel=serializer.validated_data.get('channel', 'websocket'),
                data=serializer.validated_data.get('data', {}),
                priority=serializer.validated_data.get('priority', 'medium'),
                scheduled_at=serializer.validated_data.get('scheduled_at')
            )
            
            if success:
                return Response(
                    {'message': 'Notification accepted for delivery'},
                    status=status.HTTP_202_ACCEPTED,
                )
            else:
                return Response(
                    {'error': 'Failed to send notification'},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error creating notification: {e}")
            return Response(
                {'error': 'Internal server error'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def mark_as_read(self, request, pk=None):
        """Mark notification as read"""
        notification = self.get_object()
        notification.mark_as_read()
        
        return Response({
            'message': 'Notification marked as read',
            'status': notification.status
        })
    
    @action(detail=False, methods=['post'])
    def mark_all_as_read(self, request):
        """Mark all notifications as read"""
        count = self.get_queryset().filter(
            status__in=[Notification.SENT, Notification.DELIVERED]
        ).update(
            status=Notification.READ,
            read_at=timezone.now()
        )
        
        return Response({
            'message': f'{count} notifications marked as read'
        })
    
    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """Get count of unread notifications"""
        count = self.get_queryset().filter(
            status__in=[Notification.SENT, Notification.DELIVERED]
        ).count()
        
        return Response({'unread_count': count})
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get notification statistics for user"""
        queryset = self.get_queryset()
        
        stats = {
            'total_notifications': queryset.count(),
            'sent_notifications': queryset.filter(status=Notification.SENT).count(),
            'delivered_notifications': queryset.filter(status=Notification.DELIVERED).count(),
            'failed_notifications': queryset.filter(status=Notification.FAILED).count(),
            'pending_notifications': queryset.filter(status=Notification.PENDING).count(),
            'read_notifications': queryset.filter(status=Notification.READ).count(),
            
            # Channel breakdown
            'push_notifications': queryset.filter(channel='push').count(),
            'email_notifications': queryset.filter(channel='email').count(),
            'sms_notifications': queryset.filter(channel='sms').count(),
            'websocket_notifications': queryset.filter(channel='websocket').count(),
            
            # Type breakdown
            'order_notifications': queryset.filter(
                notification_type__in=['order_confirmed', 'payment_success']
            ).count(),
            'message_notifications': queryset.filter(
                notification_type='new_message'
            ).count(),
            'marketing_notifications': queryset.filter(
                notification_type='discount_available'
            ).count(),
            'system_notifications': queryset.filter(
                notification_type__in=['market_approved', 'product_published', 'system_maintenance', 'security_alert']
            ).count(),
        }
        
        serializer = NotificationStatsSerializer(stats)
        return Response(serializer.data)


class NotificationTemplateViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing notification templates
    """
    queryset = NotificationTemplate.objects.all()
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'create':
            return NotificationTemplateCreateSerializer
        return NotificationTemplateSerializer
    
    @action(detail=True, methods=['post'])
    def test(self, request, pk=None):
        """Test a notification template"""
        template = self.get_object()
        user = request.user
        
        # Get test context
        context = request.data.get('context', {})
        
        # Send test notification
        service = NotificationService()
        success = service.send_template_notification(
            user=user,
            template_name=template.name,
            context=context,
            channel=template.channel
        )
        
        if success:
            return Response({'message': 'Test notification sent successfully'})
        else:
            return Response(
                {'error': 'Failed to send test notification'},
                status=status.HTTP_400_BAD_REQUEST
            )


class NotificationPreferenceViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing notification preferences
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Get preferences for current user"""
        return NotificationPreference.objects.filter(user=self.request.user)
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action in ['update', 'partial_update']:
            return NotificationPreferenceUpdateSerializer
        return NotificationPreferenceSerializer
    
    def get_object(self):
        """Get or create preferences for current user"""
        obj, created = NotificationPreference.objects.get_or_create(
            user=self.request.user
        )
        return obj
    
    def list(self, request, *args, **kwargs):
        """Get user preferences"""
        preferences = self.get_object()
        serializer = self.get_serializer(preferences)
        return Response(serializer.data)


class BulkNotificationView(BaseCreateView):
    """
    View for sending bulk notifications
    """
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]
    
    def get_serializer_class(self):
        return BulkNotificationSerializer
    
    def post(self, request):
        """Send bulk notifications"""
        serializer = BulkNotificationSerializer(data=request.data)
        if serializer.is_valid():
            try:
                # Get users
                users = User.objects.filter(
                    id__in=serializer.validated_data['user_ids']
                )
                
                # Send notifications
                service = NotificationService()
                results = service.send_bulk_notifications(
                    users=list(users),
                    notification_type=serializer.validated_data['notification_type'],
                    title=serializer.validated_data['title'],
                    body=serializer.validated_data['body'],
                    channel=serializer.validated_data.get('channel', 'websocket'),
                    data=serializer.validated_data.get('data', {}),
                    priority=serializer.validated_data.get('priority', 'medium'),
                    scheduled_at=serializer.validated_data.get('scheduled_at')
                )
                
                return self.success_response(
                    data={
                        'message': 'Bulk notifications processed',
                        'results': results
                    },
                    message="Bulk notifications sent successfully"
                )
                
            except Exception as e:
                logger.error(f"Error sending bulk notifications: {e}")
                return self.error_response(f"Failed to send bulk notifications: {str(e)}", 500)
        else:
            return self.error_response("Validation error", 400, str(serializer.errors))


class NotificationQueueView(APIView):
    """
    View for managing notification queue
    """
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]
    serializer_class = NotificationQueueSerializer
    
    def get(self, request):
        """Get queued notifications"""
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 20))
        
        start = (page - 1) * page_size
        end = start + page_size
        
        queued_notifications = NotificationQueue.objects.select_related(
            'notification__user'
        ).order_by('-priority', 'scheduled_at')[start:end]
        
        serializer = NotificationQueueSerializer(queued_notifications, many=True)
        
        return Response({
            'results': serializer.data,
            'page': page,
            'page_size': page_size,
            'total': NotificationQueue.objects.count()
        })
    
    def post(self, request):
        """Process notification queue"""
        batch_size = int(request.data.get('batch_size', 100))
        
        processor = NotificationQueueProcessor()
        results = processor.process_queue(batch_size)
        
        return Response({
            'message': 'Queue processed',
            'results': results
        })


class NotificationStatsView(APIView):
    """
    View for notification statistics
    """
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]
    serializer_class = NotificationStatsSerializer
    
    @method_decorator(cache_page(60 * 5))  # Cache for 5 minutes
    def get(self, request):
        """Get notification statistics"""
        # Get date range
        days = int(request.GET.get('days', 30))
        start_date = timezone.now() - timezone.timedelta(days=days)
        
        # Base queryset
        queryset = Notification.objects.filter(created_at__gte=start_date)
        
        # Calculate statistics
        stats = {
            'total_notifications': queryset.count(),
            'sent_notifications': queryset.filter(status=Notification.SENT).count(),
            'delivered_notifications': queryset.filter(status=Notification.DELIVERED).count(),
            'failed_notifications': queryset.filter(status=Notification.FAILED).count(),
            'pending_notifications': queryset.filter(status=Notification.PENDING).count(),
            'read_notifications': queryset.filter(status=Notification.READ).count(),
            
            # Channel breakdown
            'push_notifications': queryset.filter(channel='push').count(),
            'email_notifications': queryset.filter(channel='email').count(),
            'sms_notifications': queryset.filter(channel='sms').count(),
            'websocket_notifications': queryset.filter(channel='websocket').count(),
            
            # Type breakdown
            'order_notifications': queryset.filter(
                notification_type__in=['order_confirmed', 'payment_success']
            ).count(),
            'message_notifications': queryset.filter(
                notification_type='new_message'
            ).count(),
            'marketing_notifications': queryset.filter(
                notification_type='discount_available'
            ).count(),
            'system_notifications': queryset.filter(
                notification_type__in=['market_approved', 'product_published', 'system_maintenance', 'security_alert']
            ).count(),
        }
        
        # Calculate performance metrics
        total_sent = stats['sent_notifications'] + stats['delivered_notifications']
        if total_sent > 0:
            stats['success_rate'] = (stats['delivered_notifications'] / total_sent) * 100
        else:
            stats['success_rate'] = 0
        
        # Calculate retry rate
        total_with_retries = queryset.filter(retry_count__gt=0).count()
        if stats['total_notifications'] > 0:
            stats['retry_rate'] = (total_with_retries / stats['total_notifications']) * 100
        else:
            stats['retry_rate'] = 0
        
        # Calculate average delivery time
        delivered_notifications = queryset.filter(
            status=Notification.DELIVERED,
            sent_at__isnull=False,
            delivered_at__isnull=False
        )
        
        if delivered_notifications.exists():
            total_time = 0
            count = 0
            for notification in delivered_notifications:
                if notification.sent_at and notification.delivered_at:
                    duration = (notification.delivered_at - notification.sent_at).total_seconds()
                    total_time += duration
                    count += 1
            
            if count > 0:
                stats['average_delivery_time'] = total_time / count
            else:
                stats['average_delivery_time'] = 0
        else:
            stats['average_delivery_time'] = 0
        
        serializer = NotificationStatsSerializer(stats)
        return Response(serializer.data)


class NotificationCleanupView(APIView):
    """
    View for cleaning up old notifications
    """
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]
    serializer_class = NotificationCleanupSerializer
    
    def post(self, request):
        """Clean up old notifications"""
        days = int(request.data.get('days', 30))
        
        processor = NotificationQueueProcessor()
        deleted_count = processor.cleanup_old_notifications(days)
        
        return Response({
            'message': f'Cleaned up {deleted_count} old notifications',
            'deleted_count': deleted_count
        })
