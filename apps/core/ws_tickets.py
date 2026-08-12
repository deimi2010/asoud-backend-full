"""Short-lived, single-use WebSocket authentication tickets."""

from __future__ import annotations

import hashlib
import json
import secrets

import redis
from django.conf import settings


_CONSUME_SCRIPT = """
local value = redis.call('GET', KEYS[1])
if value then redis.call('DEL', KEYS[1]) end
return value
"""


_CLIENTS = {}


def get_ticket_client():
    url = settings.REDIS_URL
    client = _CLIENTS.get(url)
    if client is None:
        client = redis.Redis.from_url(
            url,
            decode_responses=True,
            socket_connect_timeout=1,
            socket_timeout=1,
            health_check_interval=30,
        )
        _CLIENTS[url] = client
    return client


class WebSocketTicketStore:
    prefix = "asoud:ws-ticket:v1"

    @classmethod
    def _key(cls, ticket):
        digest = hashlib.sha256(ticket.encode("utf-8")).hexdigest()
        return f"{cls.prefix}:{digest}"

    @classmethod
    def issue(cls, *, user_id, scope, path):
        ttl = int(getattr(settings, "ASOUD_WS_TICKET_TTL_SECONDS", 60))
        for _ in range(3):
            ticket = secrets.token_urlsafe(32)
            payload = json.dumps(
                {"user_id": str(user_id), "scope": scope, "path": path},
                separators=(",", ":"),
            )
            if get_ticket_client().set(cls._key(ticket), payload, ex=ttl, nx=True):
                return ticket, ttl
        raise redis.RedisError("Unable to allocate a unique WebSocket ticket")

    @classmethod
    def consume(cls, ticket, *, path):
        raw = get_ticket_client().eval(_CONSUME_SCRIPT, 1, cls._key(ticket))
        if not raw:
            return None
        try:
            payload = json.loads(raw)
        except (TypeError, ValueError):
            return None
        if not secrets.compare_digest(str(payload.get("path", "")), path):
            return None
        return payload
