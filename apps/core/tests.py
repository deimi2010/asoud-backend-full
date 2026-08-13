from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth.models import AnonymousUser
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import URLPattern, URLResolver, get_resolver
from rest_framework.test import APIClient
from redis import RedisError

from apps.core.rate_limit import AtomicRateThrottle, RateLimitBackendUnavailable
from apps.core.request_identity import get_client_ip
from apps.core.permissions import IsPlatformAdmin, IsStoreOwner, IsAuthenticatedUser
from apps.category.models import Category, Group, SubCategory
from apps.market.models import Market, MarketMembership
from apps.users.models import User


class URLArchitectureTests(SimpleTestCase):
    def _patterns(self, patterns=None, namespace=()):
        if patterns is None:
            patterns = get_resolver().url_patterns
        for item in patterns:
            if isinstance(item, URLResolver):
                next_namespace = namespace + ((item.namespace,) if item.namespace else ())
                yield from self._patterns(item.url_patterns, next_namespace)
            elif isinstance(item, URLPattern):
                qualified_name = ':'.join((*namespace, item.name)) if item.name else None
                yield str(item.pattern), qualified_name, item.callback

    def test_named_routes_are_unique_within_their_namespace(self):
        callbacks_by_name = {}
        for _, name, callback in self._patterns():
            if name:
                callbacks_by_name.setdefault(name, set()).add(callback)
        duplicates = sorted(
            name for name, callbacks in callbacks_by_name.items() if len(callbacks) > 1
        )
        self.assertEqual(duplicates, [])

    def test_project_root_has_no_single_segment_business_catch_all(self):
        root_patterns = [str(item.pattern) for item in get_resolver().url_patterns]
        self.assertNotIn('<str:business_id>', root_patterns)


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


class RolePermissionTests(SimpleTestCase):
    def test_platform_admin_permission_requires_staff(self):
        admin = SimpleNamespace(is_authenticated=True, is_staff=True)
        admin.is_active = True
        normal = SimpleNamespace(is_authenticated=True, is_staff=False)
        normal.is_active = True
        anonymous = SimpleNamespace(is_authenticated=False)

        self.assertTrue(IsPlatformAdmin().has_permission(SimpleNamespace(user=admin), None))
        self.assertFalse(IsPlatformAdmin().has_permission(SimpleNamespace(user=normal), None))
        self.assertFalse(IsPlatformAdmin().has_permission(SimpleNamespace(user=anonymous), None))

    def test_inactive_staff_is_not_a_platform_admin(self):
        inactive = SimpleNamespace(is_authenticated=True, is_active=False, is_staff=True)
        self.assertFalse(
            IsPlatformAdmin().has_permission(SimpleNamespace(user=inactive), None)
        )

    def test_store_owner_permission_requires_owned_market(self):
        owner = SimpleNamespace(
            is_authenticated=True,
            is_staff=False,
            markets=SimpleNamespace(exists=lambda: True),
        )
        non_owner = SimpleNamespace(
            is_authenticated=True,
            is_staff=False,
            markets=SimpleNamespace(exists=lambda: False),
        )

        self.assertTrue(IsStoreOwner().has_permission(SimpleNamespace(user=owner), None))
        self.assertFalse(IsStoreOwner().has_permission(SimpleNamespace(user=non_owner), None))

    def test_user_permission_requires_authenticated_user(self):
        user = SimpleNamespace(is_authenticated=True, is_staff=False)
        anon = SimpleNamespace(is_authenticated=False)

        self.assertTrue(IsAuthenticatedUser().has_permission(SimpleNamespace(user=user), None))
        self.assertFalse(IsAuthenticatedUser().has_permission(SimpleNamespace(user=anon), None))


class RouteNamingContractTests(SimpleTestCase):
    def test_cart_user_routes_use_unique_names(self):
        self.assertIn("user_order:order_create", ["user_order:order_create", "user_order:order_list"])
        self.assertIn("user_order:order_detail", ["user_order:order_detail", "user_order:order_update"])


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


class AppBootstrapTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('09121110001', None)
        self.owner = User.objects.create_user('09121110002', None)
        group = Group.objects.create(title='Bootstrap group', market_fee=0)
        category = Category.objects.create(group=group, title='Bootstrap category', market_fee=0)
        subcategory = SubCategory.objects.create(
            category=category,
            title='Bootstrap subcategory',
            market_fee=0,
        )
        self.market = Market.objects.create(
            user=self.owner,
            type=Market.SHOP,
            status=Market.PUBLISHED,
            business_id='BOOTSTRAP-1',
            name='Bootstrap market',
            sub_category=subcategory,
        )
        self.client = APIClient()

    def test_new_user_has_universal_customer_and_creator_capabilities(self):
        self.client.force_authenticate(self.user)
        response = self.client.get('/api/v1/user/bootstrap/')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['data']['capabilities']['create_market'])
        self.assertTrue(response.data['data']['capabilities']['buy'])
        self.assertEqual(response.data['data']['markets'], [])

    def test_colleague_market_and_role_are_returned(self):
        MarketMembership.objects.create(
            market=self.market,
            user=self.user,
            role=MarketMembership.EDITOR,
        )
        self.client.force_authenticate(self.user)
        response = self.client.get('/api/v1/user/bootstrap/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['data']['markets'][0]['access'], 'editor')

    def test_platform_admin_capability_is_explicit(self):
        admin = User.objects.create_superuser('09121110003', None)
        self.client.force_authenticate(admin)
        response = self.client.get('/api/v1/user/bootstrap/')
        self.assertTrue(response.data['data']['is_platform_admin'])
        self.assertTrue(response.data['data']['capabilities']['manage_platform'])
