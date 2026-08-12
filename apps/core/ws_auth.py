"""WebSocket authentication without long-lived credentials in URLs."""

from datetime import timedelta
from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.utils import timezone
from redis import RedisError

from apps.core.ws_tickets import WebSocketTicketStore


class WebSocketAuthMiddleware(BaseMiddleware):
    """Resolve one-time query tickets or a non-URL Token header."""

    async def __call__(self, scope, receive, send):
        query = self._query(scope)

        # A long-lived token in a URL is explicitly rejected. It must not fall
        # through to a valid session cookie because the presented credential is
        # using a retired and leak-prone contract.
        if query.get("token"):
            scope["user"] = AnonymousUser()
            return await super().__call__(scope, receive, send)

        ticket = self._first(query, "ticket")
        if ticket:
            payload = await self._consume_ticket(ticket, scope.get("path", ""))
            user = await self._get_user_by_id(payload.get("user_id")) if payload else None
            scope["user"] = user or AnonymousUser()
            return await super().__call__(scope, receive, send)

        token_key = self._header_token(scope)
        if token_key:
            user = await self._get_user(token_key)
            scope["user"] = user or AnonymousUser()

        return await super().__call__(scope, receive, send)

    @staticmethod
    def _query(scope):
        try:
            return parse_qs(scope.get("query_string", b"").decode("utf-8"))
        except UnicodeDecodeError:
            return {}

    @staticmethod
    def _first(query, key):
        values = query.get(key)
        return values[0] if values else None

    @staticmethod
    def _header_token(scope):
        headers = dict(scope.get("headers", []))
        auth_header = headers.get(b"authorization")
        if not auth_header:
            return None
        try:
            parts = auth_header.decode("ascii").split()
        except UnicodeDecodeError:
            return None
        if len(parts) == 2 and parts[0] == "Token":
            return parts[1]
        return None

    @database_sync_to_async
    def _consume_ticket(self, ticket, path):
        try:
            return WebSocketTicketStore.consume(ticket, path=path)
        except RedisError:
            return None

    @database_sync_to_async
    def _get_user_by_id(self, user_id):
        if not user_id:
            return None
        from django.contrib.auth import get_user_model

        try:
            return get_user_model().objects.get(pk=user_id, is_active=True)
        except (get_user_model().DoesNotExist, ValueError, TypeError):
            return None

    @database_sync_to_async
    def _get_user(self, token_key):
        from rest_framework.authtoken.models import Token

        try:
            token = Token.objects.select_related("user").get(key=token_key)
            ttl_seconds = getattr(
                settings, "ASOUD_TOKEN_TTL_SECONDS", 30 * 24 * 60 * 60
            )
            if token.created < timezone.now() - timedelta(seconds=ttl_seconds):
                token.delete()
                return None
            if not token.user.is_active:
                return None
            return token.user
        except Token.DoesNotExist:
            return None


# Compatibility import for existing internal tests; semantics are now the
# secure ticket/header contract above, not query-token authentication.
TokenAuthMiddleware = WebSocketAuthMiddleware
