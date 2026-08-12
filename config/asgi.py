"""
ASGI config for asoud project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')

# Initialize Django ASGI application early to ensure the AppRegistry
# is populated before importing code that may import ORM models.
django_asgi_app = get_asgi_application()

# Now import WebSocket stuff after Django is initialized
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from channels.security.websocket import AllowedHostsOriginValidator

from apps.core.ws_auth import WebSocketAuthMiddleware

# Import WebSocket routing patterns (after Django setup)
from apps.notification.urls import websocket_urlpatterns as notification_ws_patterns
from apps.chat.routing import websocket_urlpatterns as chat_ws_patterns

# Combine all WebSocket URL patterns
combined_ws_urlpatterns = notification_ws_patterns + chat_ws_patterns

# AuthMiddlewareStack resolves an optional session cookie first. The inner
# middleware then validates a one-time query ticket or a non-URL Token header.
application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AllowedHostsOriginValidator(
        AuthMiddlewareStack(
            WebSocketAuthMiddleware(
                URLRouter(
                    combined_ws_urlpatterns
                )
            )
        )
    ),
})
