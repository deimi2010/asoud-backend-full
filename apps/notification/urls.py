from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.notification.consumers import NotificationConsumer
from .views import (
    NotificationViewSet, NotificationTemplateViewSet,
    NotificationPreferenceViewSet, BulkNotificationView,
    NotificationQueueView, NotificationStatsView, NotificationCleanupView
)

# WebSocket URLs
websocket_urlpatterns = [
    path("ws/notifications", NotificationConsumer.as_asgi()),
]

# API Router
router = DefaultRouter()
router.register(r'notifications', NotificationViewSet, basename='notifications')
router.register(r'templates', NotificationTemplateViewSet, basename='templates')
router.register(r'preferences', NotificationPreferenceViewSet, basename='preferences')

# API URL patterns
urlpatterns = [
    path('api/v1/', include(router.urls)),
    path('api/v1/bulk/', BulkNotificationView.as_view(), name='bulk-notifications'),
    path('api/v1/queue/', NotificationQueueView.as_view(), name='notification-queue'),
    path('api/v1/stats/', NotificationStatsView.as_view(), name='notification-stats'),
    path('api/v1/cleanup/', NotificationCleanupView.as_view(), name='notification-cleanup'),
]