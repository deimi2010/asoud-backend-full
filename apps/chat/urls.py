"""
URL Configuration for Chat and Support System
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ChatRoomViewSet, ChatMessageViewSet, SupportTicketViewSet,
    ChatAnalyticsView, ChatSearchView
)

# API Router
router = DefaultRouter()
router.register(r'rooms', ChatRoomViewSet, basename='chatrooms')
router.register(r'messages', ChatMessageViewSet, basename='chatmessages')
router.register(r'support/tickets', SupportTicketViewSet, basename='supporttickets')

# URL patterns
urlpatterns = [
    # API endpoints
    path('api/v1/chat/', include(router.urls)),
    
    # Analytics
    path('api/v1/chat/analytics/', ChatAnalyticsView.as_view(), name='chat-analytics'),
    
    # Search
    path('api/v1/chat/search/', ChatSearchView.as_view(), name='chat-search'),
]
