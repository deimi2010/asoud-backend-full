"""
WebSocket Routing for Chat and Support System
"""

from django.urls import path
from apps.chat.consumers import ChatConsumer, SupportConsumer

websocket_urlpatterns = [
    # kwarg must be room_id: ChatConsumer.connect reads kwargs['room_id'].
    path('ws/chat/<str:room_id>/', ChatConsumer.as_asgi()),
    path('ws/support/<str:ticket_id>/', SupportConsumer.as_asgi()),
]