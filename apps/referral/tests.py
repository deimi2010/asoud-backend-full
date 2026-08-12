from django.core.cache import cache
from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from unittest.mock import patch

from apps.referral.models import Referral
from apps.users.models import User


class _RateLimitRedis:
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


class ReferralIntegrityTests(TestCase):
    create_url = '/api/v1/user/referral/create/'
    list_url = '/api/v1/user/referral/'

    def setUp(self):
        cache.clear()
        self.referrer = User.objects.create_user('09129990001', None)
        self.other_referrer = User.objects.create_user('09129990002', None)
        self.referred = User.objects.create_user('09129990003', None)
        self.client = APIClient()
        self.client.force_authenticate(self.referred)

    def test_create_is_idempotent_for_same_code(self):
        created = self.client.post(
            self.create_url,
            {'code': self.referrer.mobile_number},
            format='json',
        )
        repeated = self.client.post(
            self.create_url,
            {'code': self.referrer.mobile_number},
            format='json',
        )

        self.assertEqual(created.status_code, 201)
        self.assertEqual(repeated.status_code, 200)
        self.assertEqual(created.data['data']['id'], repeated.data['data']['id'])
        self.assertEqual(Referral.objects.count(), 1)

    def test_different_code_conflicts_after_first_application(self):
        Referral.objects.create(
            referred_by=self.referrer,
            referred_user=self.referred,
        )

        response = self.client.post(
            self.create_url,
            {'code': self.other_referrer.mobile_number},
            format='json',
        )
        invalid_after_first = self.client.post(
            self.create_url,
            {'code': '09120000000'},
            format='json',
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(invalid_after_first.status_code, 409)
        self.assertEqual(response.data['error'], invalid_after_first.data['error'])
        self.assertEqual(self.referred.referral.referred_by, self.referrer)

    def test_invalid_and_self_codes_share_non_enumerating_error(self):
        invalid = self.client.post(
            self.create_url,
            {'code': '09120000000'},
            format='json',
        )
        own = self.client.post(
            self.create_url,
            {'code': self.referred.mobile_number},
            format='json',
        )

        self.assertEqual(invalid.status_code, 400)
        self.assertEqual(own.status_code, 400)
        self.assertEqual(invalid.data['error'], own.data['error'])
        self.assertFalse(Referral.objects.exists())

    def test_list_is_self_scoped_and_does_not_expose_mobile_numbers(self):
        another_user = User.objects.create_user('09129990004', None)
        Referral.objects.create(
            referred_by=self.referrer,
            referred_user=self.referred,
        )
        Referral.objects.create(
            referred_by=self.referrer,
            referred_user=another_user,
        )
        self.client.force_authenticate(self.referrer)

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['data']['referral_count'], 2)
        self.assertEqual(
            {item['id'] for item in response.data['data']['referrees']},
            {self.referred.id, another_user.id},
        )
        self.assertTrue(
            all('mobile_number' not in item for item in response.data['data']['referrees'])
        )

    def test_create_requires_authentication(self):
        self.client.force_authenticate(user=None)

        response = self.client.post(
            self.create_url,
            {'code': self.referrer.mobile_number},
            format='json',
        )

        self.assertEqual(response.status_code, 401)
        self.assertFalse(Referral.objects.exists())

    @override_settings(
        ASOUD_RATE_LIMIT_ENABLED=True,
        ASOUD_RATE_LIMITS={'referral_create': {'user': '10/hour'}},
    )
    @patch('apps.core.rate_limit.get_rate_limit_client')
    def test_create_is_scoped_to_ten_attempts_per_hour(self, client):
        client.return_value = _RateLimitRedis()
        cache.clear()

        responses = [
            self.client.post(
                self.create_url,
                {'code': f'091200000{index:02d}'},
                format='json',
            )
            for index in range(11)
        ]

        self.assertTrue(all(response.status_code == 400 for response in responses[:10]))
        self.assertEqual(responses[10].status_code, 429)
