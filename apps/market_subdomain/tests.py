from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.category.models import Category, Group, SubCategory
from apps.market.models import Market
from apps.referral.models import StoreAccess
from apps.users.models import User

@override_settings(ALLOWED_HOSTS=['testserver', '.asoud.ir'])
class SubdomainAccessTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user('09124440001', None)
        self.buyer = User.objects.create_user('09124440002', None)
        group = Group.objects.create(title='Host group', market_fee=0)
        category = Category.objects.create(group=group, title='Host category', market_fee=0)
        subcategory = SubCategory.objects.create(
            category=category, title='Host subcategory', market_fee=0
        )
        self.market = Market.objects.create(
            user=self.owner,
            type=Market.SHOP,
            status=Market.PUBLISHED,
            business_id='host-store',
            name='Host store',
            sub_category=subcategory,
        )
        self.client = APIClient()

    def test_subdomain_requires_otp_verified_store_access(self):
        anonymous = self.client.get('/', HTTP_HOST='host-store.asoud.ir')
        self.assertEqual(anonymous.status_code, 401)

        self.client.force_authenticate(self.buyer)
        without_access = self.client.get('/', HTTP_HOST='host-store.asoud.ir')
        self.assertEqual(without_access.status_code, 404)

        StoreAccess.objects.create(user=self.buyer, market=self.market)
        allowed = self.client.get('/', HTTP_HOST='host-store.asoud.ir')
        self.assertEqual(allowed.status_code, 200)
