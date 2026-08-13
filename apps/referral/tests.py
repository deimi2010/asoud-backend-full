from django.core.cache import cache
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from unittest.mock import patch

from apps.category.models import Category, Group, SubCategory
from apps.market.models import Market
from apps.payment.models import Payment
from apps.referral.models import (
    MarketInviteLink, Referral, ReferralCommission, ReferralLevel, StoreAccess,
)
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

    def test_legacy_mobile_referral_cannot_attribute_existing_account(self):
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

        self.assertEqual(created.status_code, 400)
        self.assertEqual(repeated.status_code, 400)
        self.assertEqual(Referral.objects.count(), 0)

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

        self.assertEqual(response.status_code, 400)
        self.assertEqual(invalid_after_first.status_code, 400)
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


class MarketInviteFlowTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user('09128880001', None)
        self.visitor = User.objects.create_user('09128880002', None)
        group = Group.objects.create(title='Invite group', market_fee=0)
        category = Category.objects.create(group=group, title='Invite category', market_fee=0)
        subcategory = SubCategory.objects.create(
            category=category,
            title='Invite subcategory',
            market_fee=0,
        )
        self.market = Market.objects.create(
            user=self.owner,
            type=Market.SHOP,
            status=Market.PUBLISHED,
            business_id='INVITE-STORE',
            name='Invite store',
            sub_category=subcategory,
        )
        self.client = APIClient()

    def test_owner_creates_public_invite_and_visitor_applies_it(self):
        self.client.force_authenticate(self.owner)
        created = self.client.post(
            '/api/v1/user/referral/invites/',
            {'market_id': str(self.market.id)},
            format='json',
        )
        self.assertEqual(created.status_code, 201)

        token = created.data['token']
        self.client.force_authenticate(user=None)
        resolved = self.client.get(f'/invite/{token}/')
        self.assertEqual(resolved.status_code, 200)
        self.assertEqual(resolved.data['requires_otp'], True)
        self.assertNotIn('business_id', resolved.data)
        self.assertNotIn('market', resolved.data)

        self.client.force_authenticate(self.visitor)
        applied = self.client.post(
            '/api/v1/user/referral/create/',
            {'code': token},
            format='json',
        )
        self.assertEqual(applied.status_code, 201)
        self.assertTrue(StoreAccess.objects.filter(user=self.visitor, market=self.market).exists())
        self.assertFalse(Referral.objects.filter(referred_user=self.visitor).exists())
        self.assertEqual(MarketInviteLink.objects.get(token=token).use_count, 0)

    def test_non_owner_cannot_create_invite_for_market(self):
        self.client.force_authenticate(self.visitor)
        response = self.client.post(
            '/api/v1/user/referral/invites/',
            {'market_id': str(self.market.id)},
            format='json',
        )
        self.assertEqual(response.status_code, 404)

    def test_store_data_requires_authentication_and_market_access(self):
        endpoint = f'/api/v1/storefront/markets?id={self.market.id}'

        anonymous = self.client.get(endpoint)
        self.assertEqual(anonymous.status_code, 401)

        self.client.force_authenticate(self.visitor)
        forbidden = self.client.get(endpoint)
        self.assertEqual(forbidden.status_code, 404)

        StoreAccess.objects.create(user=self.visitor, market=self.market)
        allowed = self.client.get(endpoint)
        self.assertEqual(allowed.status_code, 200)

    @patch('apps.users.views.user_views.SMSCoreHandler.send_verification_code')
    def test_first_signup_with_invite_creates_access_and_financial_attribution(self, send):
        send.return_value = {'status': 1, 'data': None}
        invite = MarketInviteLink.objects.create(
            market=self.market,
            created_by=self.owner,
        )
        mobile = '09128880003'

        created = self.client.post(
            '/api/v1/user/pin/create/',
            {'mobile_number': mobile, 'invite_token': str(invite.token)},
            format='json',
        )
        self.assertEqual(created.status_code, 200)
        pin = send.call_args.args[1]

        verified = self.client.post(
            '/api/v1/user/pin/verify/',
            {'mobile_number': mobile, 'pin': pin},
            format='json',
        )

        self.assertEqual(verified.status_code, 200)
        user = User.objects.get(mobile_number=mobile)
        self.assertTrue(StoreAccess.objects.filter(user=user, market=self.market).exists())
        referral = Referral.objects.get(referred_user=user)
        self.assertEqual(referral.referred_by, self.owner)
        self.assertEqual(referral.invite_link, invite)
        self.assertEqual(verified.data['data']['business_id'], self.market.business_id)

    @patch('apps.users.views.user_views.SMSCoreHandler.send_verification_code')
    def test_existing_organic_account_gets_store_access_without_referral(self, send):
        send.return_value = {'status': 1, 'data': None}
        invite = MarketInviteLink.objects.create(
            market=self.market,
            created_by=self.owner,
        )

        created = self.client.post(
            '/api/v1/user/pin/create/',
            {
                'mobile_number': self.visitor.mobile_number,
                'invite_token': str(invite.token),
            },
            format='json',
        )
        self.assertEqual(created.status_code, 200)
        pin = send.call_args.args[1]
        verified = self.client.post(
            '/api/v1/user/pin/verify/',
            {'mobile_number': self.visitor.mobile_number, 'pin': pin},
            format='json',
        )

        self.assertEqual(verified.status_code, 200)
        self.assertTrue(
            StoreAccess.objects.filter(user=self.visitor, market=self.market).exists()
        )
        self.assertFalse(Referral.objects.filter(referred_user=self.visitor).exists())


class SevenLevelCommissionTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser('09125550000', None)
        self.source = User.objects.create_user('09125550001', None)
        current = self.source
        self.uplines = []
        for level in range(1, 8):
            upline = User.objects.create_user(f'091255500{level + 1:02d}', None)
            Referral.objects.create(referred_user=current, referred_by=upline)
            ReferralLevel.objects.create(level=level, percentage=level)
            self.uplines.append(upline)
            current = upline
        group = Group.objects.create(title='Commission group', market_fee=0)
        category = Category.objects.create(group=group, title='Commission category', market_fee=0)
        subcategory = SubCategory.objects.create(
            category=category, title='Commission subcategory', market_fee=0
        )
        self.market = Market.objects.create(
            user=self.source, type=Market.SHOP, status=Market.QUEUE,
            business_id='COMMISSION-STORE', name='Commission store',
            sub_category=subcategory,
        )
        self.payment = Payment.objects.create(
            user=self.source, amount='1000.00', status=Payment.COMPLETE,
            target_content_type=ContentType.objects.get_for_model(Market),
            target_id=self.market.id,
        )
        self.client = APIClient()
        self.client.force_authenticate(self.admin)

    def test_publication_creates_exactly_seven_idempotent_commissions(self):
        endpoint = f'/api/v1/admin/markets/publications/{self.market.id}/'
        payload = {'action': 'approve', 'payment_id': str(self.payment.id)}
        first = self.client.post(endpoint, payload, format='json')
        repeated = self.client.post(endpoint, payload, format='json')

        self.assertEqual(first.status_code, 200)
        self.assertEqual(repeated.status_code, 200)
        self.assertEqual(ReferralCommission.objects.count(), 7)
        for level, upline in enumerate(self.uplines, start=1):
            commission = ReferralCommission.objects.get(level=level)
            self.assertEqual(commission.beneficiary, upline)
            self.assertEqual(commission.amount, level * 10)

    def test_commission_can_be_canceled_once_but_not_reopened(self):
        from apps.referral.services import accrue_store_publication_commissions

        commission = accrue_store_publication_commissions(
            market=self.market, payment=self.payment
        )[0]
        endpoint = f'/api/v1/admin/referrals/commissions/{commission.id}/status/'
        canceled = self.client.post(endpoint, {'status': 'canceled'}, format='json')
        repeated = self.client.post(endpoint, {'status': 'canceled'}, format='json')
        reopen = self.client.post(endpoint, {'status': 'paid'}, format='json')

        self.assertEqual(canceled.status_code, 200)
        self.assertEqual(repeated.status_code, 200)
        self.assertEqual(reopen.status_code, 400)
