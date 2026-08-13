from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from apps.category.models import Category, Group, SubCategory
from apps.market.models import Market
from apps.product.models import Product
from apps.referral.models import StoreAccess
from apps.users.models import User


class PublicProductDetailTests(TestCase):
    def setUp(self):
        owner = User.objects.create_user('09125550001', None)
        group = Group.objects.create(title='Public product group', market_fee=0)
        category = Category.objects.create(
            group=group,
            title='Public product category',
            market_fee=0,
        )
        self.subcategory = SubCategory.objects.create(
            category=category,
            title='Public product subcategory',
            market_fee=0,
        )
        self.market = Market.objects.create(
            user=owner,
            type=Market.SHOP,
            status=Market.PUBLISHED,
            business_id='PUBLIC-PRODUCT-1',
            name='Public product market',
            sub_category=self.subcategory,
        )
        self.product = self.create_product('Published product')
        self.buyer = User.objects.create_user('09125550002', None)
        StoreAccess.objects.create(user=self.buyer, market=self.market)
        self.client = APIClient()
        self.client.force_authenticate(self.buyer)

    def create_product(self, name, *, status=Product.PUBLISHED, **kwargs):
        return Product.objects.create(
            market=self.market,
            type=Product.GOOD,
            name=name,
            sub_category=self.subcategory,
            stock=2,
            main_price=Decimal('1000.000'),
            colleague_price=Decimal('700.000'),
            marketer_price=Decimal('800.000'),
            maximum_sell_price=Decimal('1200.000'),
            status=status,
            sell_type=Product.ONLINE,
            ship_cost_pay_type=Product.FREE,
            **kwargs,
        )

    def test_authorized_customer_gets_only_public_product_fields(self):
        hidden_gift = self.create_product('Hidden gift', status=Product.DRAFT)
        self.product.gift_product = hidden_gift
        self.product.save(update_fields=['gift_product', 'updated_at'])

        response = self.client.get('/api/v1/storefront/products', {'id': self.product.id})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['data']['id'], str(self.product.id))
        self.assertEqual(response.data['data']['main_price'], '1000.000')
        self.assertNotIn('colleague_price', response.data['data'])
        self.assertNotIn('marketer_price', response.data['data'])
        self.assertNotIn('maximum_sell_price', response.data['data'])
        self.assertNotIn('status', response.data['data'])
        self.assertIsNone(response.data['data']['gift_product'])

    def test_unpublished_product_or_market_is_not_public(self):
        draft = self.create_product('Draft product', status=Product.DRAFT)
        draft_response = self.client.get('/api/v1/storefront/products', {'id': draft.id})

        self.market.status = Market.INACTIVE
        self.market.save(update_fields=['status', 'updated_at'])
        hidden_market_response = self.client.get(
            '/api/v1/storefront/products',
            {'id': self.product.id},
        )

        self.assertEqual(draft_response.status_code, 404)
        self.assertEqual(hidden_market_response.status_code, 404)

    def test_invalid_id_is_a_validation_error(self):
        response = self.client.get('/api/v1/storefront/products', {'id': 'not-a-uuid'})

        self.assertEqual(response.status_code, 400)
        self.assertIn('id', response.data['details'])

    def test_anonymous_customer_cannot_fetch_product_data(self):
        self.client.force_authenticate(user=None)
        response = self.client.get('/api/v1/storefront/products', {'id': self.product.id})
        self.assertEqual(response.status_code, 401)
