from unittest.mock import patch

from asgiref.sync import async_to_sync
from django.contrib.auth.models import AnonymousUser
from django.test import TestCase, TransactionTestCase, override_settings
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from apps.chat.models import ChatParticipant, ChatRoom
from apps.core.ws_auth import WebSocketAuthMiddleware
from apps.core.ws_tickets import WebSocketTicketStore
from apps.users.models import User


class _TicketRedis:
    def __init__(self):
        self.values = {}

    def set(self, key, value, ex, nx):
        if nx and key in self.values:
            return False
        self.values[key] = value
        return True

    def eval(self, script, key_count, key):
        return self.values.pop(key, None)


class WebSocketTicketStoreTests(TestCase):
    @override_settings(ASOUD_WS_TICKET_TTL_SECONDS=60)
    def test_ticket_is_path_bound_and_single_use(self):
        backend = _TicketRedis()
        with patch("apps.core.ws_tickets.get_ticket_client", return_value=backend):
            wrong_ticket, ttl = WebSocketTicketStore.issue(
                user_id=7,
                scope="chat",
                path="/ws/chat/room-id/",
            )
            wrong_path = WebSocketTicketStore.consume(
                wrong_ticket, path="/ws/notifications"
            )
            ticket, _ = WebSocketTicketStore.issue(
                user_id=7,
                scope="chat",
                path="/ws/chat/room-id/",
            )
            accepted = WebSocketTicketStore.consume(
                ticket, path="/ws/chat/room-id/"
            )
            replay = WebSocketTicketStore.consume(
                ticket, path="/ws/chat/room-id/"
            )

        self.assertEqual(ttl, 60)
        self.assertIsNone(wrong_path)
        self.assertEqual(accepted["user_id"], "7")
        self.assertIsNone(replay)


class AuthenticationBoundaryTests(TransactionTestCase):
    def setUp(self):
        self.user = User.objects.create_user("09120000811", None)
        self.other = User.objects.create_user("09120000812", None)
        self.token = Token.objects.create(user=self.user)
        self.client = APIClient()

    def test_logout_revokes_server_token(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")

        response = self.client.post("/api/v1/user/logout/", {}, format="json")

        self.assertEqual(response.status_code, 204)
        self.assertFalse(Token.objects.filter(pk=self.token.pk).exists())

    @patch("apps.users.views.user_views.WebSocketTicketStore.issue")
    def test_chat_ticket_requires_membership_and_is_path_bound(self, issue):
        issue.return_value = ("one-time-ticket", 60)
        room = ChatRoom.objects.create(
            name="Secure room",
            room_type=ChatRoom.GROUP,
            status=ChatRoom.ACTIVE,
            created_by=self.user,
        )
        ChatParticipant.objects.create(
            chat_room=room,
            user=self.user,
            role=ChatParticipant.OWNER,
        )
        self.client.force_authenticate(self.user)

        allowed = self.client.post(
            "/api/v1/user/ws-ticket/",
            {"scope": "chat", "room_id": str(room.id)},
            format="json",
        )
        self.client.force_authenticate(self.other)
        hidden = self.client.post(
            "/api/v1/user/ws-ticket/",
            {"scope": "chat", "room_id": str(room.id)},
            format="json",
        )

        self.assertEqual(allowed.status_code, 201)
        self.assertEqual(allowed.data["data"]["expires_in"], 60)
        self.assertEqual(allowed.data["data"]["path"], f"/ws/chat/{room.id}/")
        self.assertEqual(hidden.status_code, 404)
        issue.assert_called_once_with(
            user_id=self.user.pk,
            scope="chat",
            path=f"/ws/chat/{room.id}/",
        )

    def test_query_token_is_rejected_even_when_it_is_valid(self):
        captured = {}

        async def inner(scope, receive, send):
            captured["user"] = scope.get("user")

        middleware = WebSocketAuthMiddleware(inner)
        scope = {
            "type": "websocket",
            "path": "/ws/notifications",
            "query_string": f"token={self.token.key}".encode(),
            "headers": [],
            "user": self.user,
        }

        async_to_sync(middleware)(scope, None, None)

        self.assertIsInstance(captured["user"], AnonymousUser)

    @patch("apps.core.ws_auth.WebSocketTicketStore.consume")
    def test_ticket_resolves_only_an_active_user(self, consume):
        consume.return_value = {
            "user_id": str(self.user.pk),
            "scope": "notifications",
            "path": "/ws/notifications",
        }
        captured = {}

        async def inner(scope, receive, send):
            captured["user"] = scope.get("user")

        middleware = WebSocketAuthMiddleware(inner)
        scope = {
            "type": "websocket",
            "path": "/ws/notifications",
            "query_string": b"ticket=opaque",
            "headers": [],
            "user": AnonymousUser(),
        }

        async_to_sync(middleware)(scope, None, None)

        self.assertEqual(captured["user"], self.user)
        consume.assert_called_once_with("opaque", path="/ws/notifications")
