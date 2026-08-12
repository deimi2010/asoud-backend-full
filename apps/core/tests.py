from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth.models import AnonymousUser
from django.test import SimpleTestCase, TestCase, override_settings
from rest_framework.test import APIClient
from redis import RedisError

from apps.core.rate_limit import AtomicRateThrottle, RateLimitBackendUnavailable
from apps.core.request_identity import get_client_ip
from apps.users.models import User


class _AtomicFakeRedis:
    def __init__(self):
        self.counts = {}

    def eval(self, script, key_count, *values):
        keys = values[:key_count]
        arguments = values[key_count:]
        for index, key in enumerate(keys):
            limit = int(arguments[index * 2])
            if self.counts.get(key, 0) >= limit:
                return [0, int(arguments[index * 2 + 1])]
        for key in keys:
            self.counts[key] = self.counts.get(key, 0) + 1
        return [1, 0]


class RequestIdentityTests(SimpleTestCase):
    def test_untrusted_peer_cannot_spoof_forwarded_ip(self):
        request = SimpleNamespace(
            META={
                "REMOTE_ADDR": "203.0.113.10",
                "HTTP_X_REAL_IP": "198.51.100.7",
                "HTTP_X_FORWARDED_FOR": "198.51.100.8",
            }
        )

        self.assertEqual(get_client_ip(request), "203.0.113.10")

    @override_settings(ASOUD_TRUSTED_PROXY_CIDRS=("10.0.0.0/8",))
    def test_trusted_peer_may_supply_valid_overwritten_real_ip(self):
        request = SimpleNamespace(
            META={"REMOTE_ADDR": "10.0.0.3", "HTTP_X_REAL_IP": "198.51.100.7"}
        )

        self.assertEqual(get_client_ip(request), "198.51.100.7")


class AtomicRateThrottleTests(SimpleTestCase):
    def request(self, *, authenticated=False):
        user = SimpleNamespace(is_authenticated=authenticated, pk=7)
        return SimpleNamespace(
            path="/api/v1/user/pin/create/",
            method="POST",
            user=user,
            META={"REMOTE_ADDR": "203.0.113.10"},
            data={"mobile_number": "09120000000"},
        )

    @override_settings(
        ASOUD_RATE_LIMIT_ENABLED=True,
        ASOUD_RATE_LIMITS={"pin_create": {"mobile": "2/hour", "ip": "3/hour"}},
        ASOUD_RATE_LIMIT_FAIL_CLOSED_SCOPES=("pin_create",),
    )
    def test_all_identifiers_are_checked_and_n_plus_one_is_rejected(self):
        backend = _AtomicFakeRedis()
        view = SimpleNamespace(throttle_scope="pin_create")

        with patch("apps.core.rate_limit.get_rate_limit_client", return_value=backend):
            first = AtomicRateThrottle()
            second = AtomicRateThrottle()
            third = AtomicRateThrottle()
            self.assertTrue(first.allow_request(self.request(), view))
            self.assertTrue(second.allow_request(self.request(), view))
            self.assertFalse(third.allow_request(self.request(), view))
            self.assertEqual(third.wait(), 3600)

    @override_settings(
        ASOUD_RATE_LIMIT_ENABLED=True,
        ASOUD_RATE_LIMITS={"pin_create": {"ip": "2/hour"}},
        ASOUD_RATE_LIMIT_FAIL_CLOSED_SCOPES=("pin_create",),
    )
    def test_sensitive_scope_fails_closed_when_redis_is_unavailable(self):
        throttle = AtomicRateThrottle()
        view = SimpleNamespace(throttle_scope="pin_create")
        with patch.object(throttle, "_check_limits", side_effect=RedisError):
            with self.assertRaises(RateLimitBackendUnavailable):
                throttle.allow_request(self.request(), view)

    @override_settings(
        ASOUD_RATE_LIMIT_ENABLED=True,
        ASOUD_RATE_LIMITS={"anonymous_read": {"ip": "2/minute"}},
        ASOUD_RATE_LIMIT_FAIL_CLOSED_SCOPES=(),
    )
    def test_public_read_uses_explicit_availability_policy(self):
        request = self.request()
        request.method = "GET"
        request.path = "/api/v1/"
        request.user = AnonymousUser()
        throttle = AtomicRateThrottle()
        with patch.object(throttle, "_check_limits", side_effect=RedisError):
            self.assertTrue(throttle.allow_request(request, SimpleNamespace()))


class HealthContractTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_liveness_has_no_dependency_or_system_details(self):
        response = self.client.get("/livez")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {"status": "ok"})

    @patch("config.views._dependencies_ready", return_value=False)
    def test_readiness_failure_is_minimal(self, ready):
        response = self.client.get("/readyz")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.data, {"status": "not_ready"})
        serialized = str(response.data).lower()
        for forbidden in ("exception", "database", "redis", "memory", "disk", "version"):
            self.assertNotIn(forbidden, serialized)

    def test_security_diagnostics_are_staff_only(self):
        anonymous_audit = self.client.get("/security/audit/")
        anonymous_rate = self.client.get("/rate-limit/")
        staff = User.objects.create_user("09120000801", None, is_staff=True)
        self.client.force_authenticate(staff)
        staff_audit = self.client.get("/security/audit/")
        staff_rate = self.client.get("/rate-limit/")

        self.assertIn(anonymous_audit.status_code, (401, 403))
        self.assertIn(anonymous_rate.status_code, (401, 403))
        self.assertEqual(staff_audit.status_code, 200)
        self.assertEqual(staff_rate.status_code, 200)
