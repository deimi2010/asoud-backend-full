from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.notification.consumers import NotificationConsumer
from .views import (
    NotificationViewSet, NotificationTemplateViewSet,
    NotificationPreferenceViewSet, BulkNotificationView,
    NotificationQueueView, NotificationStatsView, NotificationCleanupView,
    DeviceInstallationViewSet,
)

app_name = 'notification'

# WebSocket URLs
websocket_urlpatterns = [
    path("ws/notifications", NotificationConsumer.as_asgi()),
]

# API Router
router = DefaultRouter()
router.register(r'notifications', NotificationViewSet, basename='notifications')
router.register(r'templates', NotificationTemplateViewSet, basename='templates')
router.register(r'preferences', NotificationPreferenceViewSet, basename='preferences')
router.register(r'devices', DeviceInstallationViewSet, basename='devices')

# API URL patterns
urlpatterns = [
    path('', include(router.urls)),
    path('bulk/', BulkNotificationView.as_view(), name='bulk'),
    path('queue/', NotificationQueueView.as_view(), name='queue'),
    path('stats/', NotificationStatsView.as_view(), name='stats'),
    path('cleanup/', NotificationCleanupView.as_view(), name='cleanup'),
]
