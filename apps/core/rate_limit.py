"""Atomic Redis-backed throttling for REST security boundaries."""

from __future__ import annotations

import hashlib
import hmac
import logging
from math import ceil

import redis
from django.conf import settings
from rest_framework.exceptions import APIException
from rest_framework.throttling import BaseThrottle

from apps.core.request_identity import get_client_ip


logger = logging.getLogger(__name__)


class RateLimitBackendUnavailable(APIException):
    status_code = 503
    default_detail = "Request safety service is unavailable."
    default_code = "rate_limit_unavailable"


_ATOMIC_LIMIT_SCRIPT = """
local item_count = #KEYS
for index = 1, item_count do
    local limit = tonumber(ARGV[(index - 1) * 2 + 1])
    local current = tonumber(redis.call('GET', KEYS[index]) or '0')
    if current >= limit then
        local retry_after = redis.call('TTL', KEYS[index])
        if retry_after < 1 then retry_after = tonumber(ARGV[(index - 1) * 2 + 2]) end
        return {0, retry_after}
    end
end
for index = 1, item_count do
    local window = tonumber(ARGV[(index - 1) * 2 + 2])
    local current = redis.call('INCR', KEYS[index])
    if current == 1 or redis.call('TTL', KEYS[index]) < 1 then
        redis.call('EXPIRE', KEYS[index], window)
    end
end
return {1, 0}
"""


_CLIENTS = {}


def get_rate_limit_client():
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


def _parse_rate(rate):
    try:
        amount, period = rate.split("/", 1)
        limit = int(amount)
    except (AttributeError, TypeError, ValueError) as exc:
        raise ValueError(f"Invalid rate limit: {rate!r}") from exc

    periods = {
        "s": 1,
        "sec": 1,
        "second": 1,
        "m": 60,
        "min": 60,
        "minute": 60,
        "h": 3600,
        "hour": 3600,
        "d": 86400,
        "day": 86400,
    }
    window = periods.get(period.lower())
    if limit < 1 or window is None:
        raise ValueError(f"Invalid rate limit: {rate!r}")
    return limit, window


def _digest_identity(kind, value):
    secret = getattr(settings, "ASOUD_RATE_LIMIT_KEY_SECRET", settings.SECRET_KEY)
    payload = f"{kind}:{value}".encode("utf-8")
    return hmac.new(str(secret).encode("utf-8"), payload, hashlib.sha256).hexdigest()


class AtomicRateThrottle(BaseThrottle):
    """Apply all configured identities for a scope in one Redis operation."""

    def __init__(self):
        self.retry_after = None

    def _scope(self, request, view):
        explicit = getattr(view, "throttle_scope", None)
        if explicit:
            return explicit

        path = request.path.rstrip("/") + "/"
        if request.method not in ("GET", "HEAD", "OPTIONS"):
            if path.startswith("/api/v1/user/payments/") or path.startswith(
                "/api/v1/wallet/"
            ):
                return "payment_mutation"
        if request.user and request.user.is_authenticated:
            return "authenticated_read"
        return "anonymous_read"

    def _identity(self, request, kind):
        if kind == "ip":
            return get_client_ip(request)
        if kind == "user":
            user = getattr(request, "user", None)
            return str(user.pk) if user and user.is_authenticated else None
        if kind == "mobile":
            value = request.data.get("mobile_number") if hasattr(request, "data") else None
            return value.strip() if isinstance(value, str) else None
        return None

    def _limits(self, request, scope):
        configured = getattr(settings, "ASOUD_RATE_LIMITS", {}).get(scope, {})
        limits = []
        environment = getattr(settings, "ENVIRONMENT", "default")
        for kind, rate in configured.items():
            identity = self._identity(request, kind)
            if not identity:
                continue
            limit, window = _parse_rate(rate)
            digest = _digest_identity(kind, identity)
            key = f"asoud:rate:v1:{environment}:{scope}:{kind}:{digest}"
            limits.append((key, limit, window))
        return limits

    def _check_limits(self, limits):
        keys = [item[0] for item in limits]
        arguments = []
        for _, limit, window in limits:
            arguments.extend((limit, window))
        allowed, retry_after = get_rate_limit_client().eval(
            _ATOMIC_LIMIT_SCRIPT,
            len(keys),
            *keys,
            *arguments,
        )
        return bool(allowed), int(retry_after)

    def allow_request(self, request, view):
        if not getattr(settings, "ASOUD_RATE_LIMIT_ENABLED", True):
            return True

        scope = self._scope(request, view)
        view._asoud_rate_limit_scope = scope
        limits = self._limits(request, scope)
        if not limits:
            return True

        try:
            allowed, retry_after = self._check_limits(limits)
        except (redis.RedisError, OSError, TimeoutError):
            logger.error("Rate-limit Redis backend unavailable for scope=%s", scope)
            fail_closed = set(
                getattr(settings, "ASOUD_RATE_LIMIT_FAIL_CLOSED_SCOPES", ())
            )
            if scope in fail_closed:
                raise RateLimitBackendUnavailable()
            return True

        if not allowed:
            self.retry_after = max(1, retry_after)
        return allowed

    def wait(self):
        return ceil(self.retry_after) if self.retry_after is not None else None
