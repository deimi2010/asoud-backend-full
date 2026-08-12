from datetime import timedelta
from unittest.mock import patch

from django.core.cache import cache
from django.test import TestCase, TransactionTestCase, override_settings
from django.utils import timezone
from asgiref.sync import async_to_sync
from rest_framework.authtoken.models import Token
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.test import APIClient, APIRequestFactory

from apps.users.models import BankInfo, User, UserBankInfo, UserProfile
from apps.users.token_authentication import ExpiringTokenAuthentication
from apps.users.views.user_views import (
    PinCreateAPIView,
    PinVerifyAPIView,
    _otp_cache_key,
)
from apps.core.ws_auth import TokenAuthMiddleware
from apps.notification.validator import validate_user


class SelfProfileTests(TestCase):
    url = "/api/v1/user/profile/"

    def setUp(self):
        self.user = User.objects.create_user("09120000901", None)
        self.other = User.objects.create_user("09120000902", None)
        self.client = APIClient()

    def test_get_requires_authentication(self):
        self.assertEqual(self.client.get(self.url).status_code, 401)

    def test_get_returns_real_mobile_and_nullable_profile(self):
        self.client.force_authenticate(self.user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data["data"]["mobile_number"], self.user.mobile_number
        )
        self.assertIsNone(response.data["data"]["profile"])

    def test_create_requires_valid_national_code_and_ignores_user_fields(self):
        self.client.force_authenticate(self.user)
        missing = self.client.put(self.url, {"address": "Tehran"}, format="json")
        invalid = self.client.put(
            self.url,
            {"national_code": "123", "address": "Tehran"},
            format="json",
        )
        non_ascii = self.client.put(
            self.url,
            {
                "national_code": (
                    "\u06f1\u06f2\u06f3\u06f4\u06f5\u06f6\u06f7\u06f8\u06f9\u06f0"
                ),
                "address": "Tehran",
            },
            format="json",
        )
        created = self.client.put(
            self.url,
            {
                "national_code": "1234567890",
                "address": "Tehran",
                "mobile_number": self.other.mobile_number,
                "user": self.other.id,
            },
            format="json",
        )

        self.assertEqual(missing.status_code, 400)
        self.assertEqual(invalid.status_code, 400)
        self.assertEqual(non_ascii.status_code, 400)
        self.assertEqual(created.status_code, 200)
        profile = UserProfile.objects.get()
        self.assertEqual(profile.user, self.user)
        self.assertEqual(created.data["data"]["mobile_number"], self.user.mobile_number)

    def test_unsupported_iban_is_not_persisted(self):
        profile = UserProfile.objects.create(
            user=self.user,
            national_code="1234567890",
        )
        self.client.force_authenticate(self.user)

        response = self.client.put(
            self.url,
            {"address": "New", "iban_number": "IR123456789012345678901234"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        profile.refresh_from_db()
        self.assertIsNone(profile.address)
        self.assertIsNone(profile.iban_number)

    def test_partial_update_preserves_identity_and_required_fields(self):
        profile = UserProfile.objects.create(
            user=self.user,
            national_code="1234567890",
            address="Old",
        )
        self.client.force_authenticate(self.user)

        response = self.client.put(self.url, {"address": "New"}, format="json")

        self.assertEqual(response.status_code, 200)
        profile.refresh_from_db()
        self.assertEqual(profile.address, "New")
        self.assertEqual(profile.national_code, "1234567890")
        self.assertEqual(profile.user, self.user)


class UserBankInfoTests(TestCase):
    catalog_url = "/api/v1/user/bank-info/list/"
    list_url = "/api/v1/user/bank/info/list/"
    create_url = "/api/v1/user/bank/info/create/"

    def setUp(self):
        self.user = User.objects.create_user("09120000911", None)
        self.other = User.objects.create_user("09120000912", None)
        self.bank = BankInfo.objects.create(name="Mellat")
        self.other_bank = BankInfo.objects.create(name="Melli")
        self.client = APIClient()

    def payload(self, **overrides):
        data = {
            "bank_info": str(self.bank.id),
            "card_number": "6037997512345670",
            "account_number": "123456789",
            "iban": "IR641234567890123456789012",
            "full_name": "Test User",
            "branch_id": 1,
            "branch_name": "Central",
            "description": "Primary",
        }
        data.update(overrides)
        return data

    def create_bank_info(self, user=None):
        return UserBankInfo.objects.create(
            user=user or self.user,
            bank_info=self.bank,
            card_number=(
                "6037997512345670" if user is not self.other else "6037997587654329"
            ),
            account_number="123456789" if user is not self.other else "987654321",
            iban="IR641234567890123456789012",
            full_name="Test User",
            branch_id=1,
            branch_name="Central",
        )

    def test_catalog_is_public_but_user_list_requires_authentication(self):
        catalog = self.client.get(self.catalog_url)
        private_list = self.client.get(self.list_url)

        self.assertEqual(catalog.status_code, 200)
        self.assertEqual(
            {bank["name"] for bank in catalog.data["data"]},
            {"Mellat", "Melli"},
        )
        self.assertEqual(private_list.status_code, 401)

    def test_create_validates_financial_identifiers_and_binds_request_user(self):
        self.client.force_authenticate(self.user)
        invalid_card = self.client.post(
            self.create_url,
            self.payload(card_number="۱۲۳۴۵۶۷۸۹۰۱۲۳۴۵۶"),
            format="json",
        )
        invalid_iban = self.client.post(
            self.create_url,
            self.payload(iban="IR123"),
            format="json",
        )
        invalid_checksum = self.client.post(
            self.create_url,
            self.payload(card_number="6037997512345678"),
            format="json",
        )
        zero_card = self.client.post(
            self.create_url,
            self.payload(card_number="0000000000000000"),
            format="json",
        )
        created = self.client.post(
            self.create_url,
            self.payload(user=self.other.id),
            format="json",
        )

        self.assertEqual(invalid_card.status_code, 400)
        self.assertEqual(invalid_iban.status_code, 400)
        self.assertEqual(invalid_checksum.status_code, 400)
        self.assertEqual(zero_card.status_code, 400)
        self.assertEqual(created.status_code, 201)
        saved = UserBankInfo.objects.get()
        self.assertEqual(saved.user, self.user)
        self.assertNotIn("user", created.data["data"])
        self.assertEqual(created.data["data"]["bank_info_id"], str(self.bank.id))

    def test_list_detail_update_and_delete_share_one_explicit_shape(self):
        info = self.create_bank_info()
        self.client.force_authenticate(self.user)

        listed = self.client.get(self.list_url)
        detailed = self.client.get(
            f"/api/v1/user/bank/info/detail/{info.id}/"
        )
        updated = self.client.put(
            f"/api/v1/user/bank/info/update/{info.id}/",
            {"full_name": "Updated", "bank_info": str(self.other_bank.id)},
            format="json",
        )
        deleted = self.client.delete(
            f"/api/v1/user/bank/info/delete/{info.id}/"
        )

        self.assertEqual(listed.status_code, 200)
        self.assertEqual(detailed.status_code, 200)
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(deleted.status_code, 204)
        self.assertNotIn("user", listed.data["data"][0])
        self.assertEqual(updated.data["data"]["full_name"], "Updated")
        self.assertEqual(
            updated.data["data"]["bank_info_id"], str(self.other_bank.id)
        )
        self.assertFalse(UserBankInfo.objects.exists())

    def test_cross_user_detail_update_and_delete_are_hidden(self):
        foreign = self.create_bank_info(user=self.other)
        self.client.force_authenticate(self.user)
        base = "/api/v1/user/bank/info"

        detailed = self.client.get(f"{base}/detail/{foreign.id}/")
        updated = self.client.put(
            f"{base}/update/{foreign.id}/",
            {"full_name": "Stolen"},
            format="json",
        )
        deleted = self.client.delete(f"{base}/delete/{foreign.id}/")

        self.assertEqual(detailed.status_code, 404)
        self.assertEqual(updated.status_code, 404)
        self.assertEqual(deleted.status_code, 404)
        foreign.refresh_from_db()
        self.assertEqual(foreign.full_name, "Test User")


class OTPSecurityTests(TransactionTestCase):
    def setUp(self):
        cache.clear()
        self.factory = APIRequestFactory()
        self.mobile = "09120000101"

    @patch("apps.users.views.user_views.SMSCoreHandler.send_verification_code")
    def test_otp_is_hashed_not_logged_or_returned_and_is_single_use(self, send):
        send.return_value = {"status": 1, "data": None}
        create_request = self.factory.post(
            "/users/pin/create/",
            {"mobile_number": self.mobile},
            format="json",
        )

        create_response = PinCreateAPIView.as_view()(create_request)

        self.assertEqual(create_response.status_code, 200)
        self.assertEqual(create_response.data["data"], {})
        sent_pin = send.call_args.args[1]
        self.assertEqual(len(sent_pin), 4)
        self.assertNotEqual(cache.get(_otp_cache_key(self.mobile)), sent_pin)
        user = User.objects.get(mobile_number=self.mobile)
        self.assertIsNone(user.pin)
        self.assertIsNone(user.pin_expiry)

        old_token = Token.objects.create(user=user)
        verify_request = self.factory.post(
            "/users/pin/verify/",
            {"mobile_number": self.mobile, "pin": sent_pin},
            format="json",
        )
        verify_response = PinVerifyAPIView.as_view()(verify_request)

        self.assertEqual(verify_response.status_code, 200)
        new_token = Token.objects.get(user=user)
        self.assertNotEqual(new_token.key, old_token.key)
        self.assertIsNone(cache.get(_otp_cache_key(self.mobile)))

        replay_request = self.factory.post(
            "/users/pin/verify/",
            {"mobile_number": self.mobile, "pin": sent_pin},
            format="json",
        )
        replay_response = PinVerifyAPIView.as_view()(replay_request)
        self.assertEqual(replay_response.status_code, 401)

    @patch("apps.users.views.user_views.SMSCoreHandler.send_verification_code")
    def test_delivery_failure_does_not_create_user_or_valid_otp(self, send):
        send.return_value = {"status": 0, "data": None}
        request = self.factory.post(
            "/users/pin/create/",
            {"mobile_number": self.mobile},
            format="json",
        )

        response = PinCreateAPIView.as_view()(request)

        self.assertEqual(response.status_code, 503)
        self.assertFalse(User.objects.filter(mobile_number=self.mobile).exists())
        self.assertIsNone(cache.get(_otp_cache_key(self.mobile)))

    @override_settings(
        DEBUG=False,
        OTP_ALLOW_LOCAL_CACHE=False,
        CACHES={
            "default": {
                "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
                "LOCATION": "unsafe-production-cache",
            }
        },
    )
    @patch("apps.users.views.user_views.SMSCoreHandler.send_verification_code")
    def test_production_otp_fails_closed_without_shared_redis(self, send):
        request = self.factory.post(
            "/users/pin/create/",
            {"mobile_number": self.mobile},
            format="json",
        )

        response = PinCreateAPIView.as_view()(request)

        self.assertEqual(response.status_code, 503)
        send.assert_not_called()

    @patch("apps.users.views.user_views.SMSCoreHandler.send_verification_code")
    def test_concurrent_otp_issuance_cannot_overwrite_or_delete_active_issue(
        self, send
    ):
        otp_key = _otp_cache_key(self.mobile)
        cache.set(f"{otp_key}:issuing", True, 60)
        request = self.factory.post(
            "/users/pin/create/",
            {"mobile_number": self.mobile},
            format="json",
        )

        response = PinCreateAPIView.as_view()(request)

        self.assertEqual(response.status_code, 429)
        send.assert_not_called()

    @override_settings(ASOUD_TOKEN_TTL_SECONDS=60)
    def test_expired_token_is_rejected_and_deleted(self):
        user = User.objects.create_user(self.mobile, None)
        token = Token.objects.create(user=user)
        Token.objects.filter(key=token.key).update(
            created=timezone.now() - timedelta(seconds=61)
        )

        with self.assertRaises(AuthenticationFailed):
            ExpiringTokenAuthentication().authenticate_credentials(token.key)

        self.assertFalse(Token.objects.filter(key=token.key).exists())

    @override_settings(ASOUD_TOKEN_TTL_SECONDS=60)
    def test_expired_websocket_token_is_rejected(self):
        user = User.objects.create_user(self.mobile, None)
        token = Token.objects.create(user=user)
        Token.objects.filter(key=token.key).update(
            created=timezone.now() - timedelta(seconds=61)
        )
        middleware = TokenAuthMiddleware(lambda scope, receive, send: None)

        resolved_user = async_to_sync(middleware._get_user)(token.key)

        self.assertIsNone(resolved_user)
        self.assertFalse(Token.objects.filter(key=token.key).exists())

    @override_settings(ASOUD_TOKEN_TTL_SECONDS=60)
    def test_expired_notification_socket_token_is_rejected(self):
        user = User.objects.create_user(self.mobile, None)
        token = Token.objects.create(user=user)
        Token.objects.filter(key=token.key).update(
            created=timezone.now() - timedelta(seconds=61)
        )

        middleware = TokenAuthMiddleware(lambda scope, receive, send: None)
        resolved_user = async_to_sync(middleware._get_user)(token.key)

        self.assertIsNone(resolved_user)
        self.assertFalse(Token.objects.filter(key=token.key).exists())

    @patch("apps.users.views.user_views.SMSCoreHandler.send_verification_code")
    def test_inactive_user_cannot_exchange_otp_for_token(self, send):
        send.return_value = {"status": 1, "data": None}
        user = User.objects.create_user(self.mobile, None, is_active=False)
        create_request = self.factory.post(
            "/users/pin/create/",
            {"mobile_number": self.mobile},
            format="json",
        )
        PinCreateAPIView.as_view()(create_request)
        sent_pin = send.call_args.args[1]
        verify_request = self.factory.post(
            "/users/pin/verify/",
            {"mobile_number": self.mobile, "pin": sent_pin},
            format="json",
        )

        response = PinVerifyAPIView.as_view()(verify_request)

        self.assertEqual(response.status_code, 401)
        self.assertFalse(Token.objects.filter(user=user).exists())

    def test_inactive_user_tokens_are_rejected_on_websockets(self):
        user = User.objects.create_user(self.mobile, None, is_active=False)
        token = Token.objects.create(user=user)
        middleware = TokenAuthMiddleware(lambda scope, receive, send: None)

        core_user = async_to_sync(middleware._get_user)(token.key)
        notification_user = async_to_sync(validate_user)(
            {"query_string": b"", "user": None}
        )

        self.assertIsNone(core_user)
        self.assertIsNone(notification_user)
