from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from apps.category.models import Category, Group, SubCategory
from apps.market.models import (
    Market,
    MarketBookmark,
    MarketContact,
    MarketLike,
    MarketReport,
    MarketView,
)
from apps.product.models import Product, ProductBookmark, ProductLike, ProductReport
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

    def test_product_interactions_are_persisted_and_returned(self):
        like_url = f'/api/v1/storefront/products/{self.product.id}/like'
        bookmark_url = f'/api/v1/storefront/products/{self.product.id}/bookmark'
        report_url = f'/api/v1/storefront/products/{self.product.id}/report'

        like = self.client.post(like_url)
        bookmark = self.client.post(bookmark_url)
        report = self.client.post(report_url, {'description': 'Incorrect content'})
        detail = self.client.get('/api/v1/storefront/products', {'id': self.product.id})

        self.assertEqual(like.status_code, 200)
        self.assertTrue(like.data['is_liked'])
        self.assertEqual(bookmark.status_code, 200)
        self.assertTrue(bookmark.data['is_bookmarked'])
        self.assertEqual(report.status_code, 201)
        self.assertTrue(ProductLike.objects.get().is_active)
        self.assertTrue(ProductBookmark.objects.get().is_active)
        self.assertEqual(ProductReport.objects.get().description, 'Incorrect content')
        self.assertTrue(detail.data['data']['is_liked'])
        self.assertTrue(detail.data['data']['is_bookmarked'])
        self.assertEqual(detail.data['data']['likes_count'], 1)
        self.assertGreaterEqual(detail.data['data']['views_count'], 1)

    def test_like_and_bookmark_are_toggles(self):
        like_url = f'/api/v1/storefront/products/{self.product.id}/like'
        bookmark_url = f'/api/v1/storefront/products/{self.product.id}/bookmark'

        self.client.post(like_url)
        second_like = self.client.post(like_url)
        self.client.post(bookmark_url)
        second_bookmark = self.client.post(bookmark_url)

        self.assertFalse(second_like.data['is_liked'])
        self.assertEqual(second_like.data['likes_count'], 0)
        self.assertFalse(second_bookmark.data['is_bookmarked'])


class PublicMarketInteractionTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user('09125550101', None)
        self.buyer = User.objects.create_user('09125550102', None)
        group = Group.objects.create(title='Market interaction group', market_fee=0)
        category = Category.objects.create(
            group=group,
            title='Market interaction category',
            market_fee=0,
        )
        subcategory = SubCategory.objects.create(
            category=category,
            title='Market interaction subcategory',
            market_fee=0,
        )
        self.market = Market.objects.create(
            user=self.owner,
            type=Market.SHOP,
            status=Market.PUBLISHED,
            business_id='MARKET-INTERACTION-1',
            name='Interaction market',
            sub_category=subcategory,
        )
        MarketContact.objects.create(
            market=self.market,
            first_mobile_number='09120000000',
            telephone='02112345678',
            fax='02112345679',
            email='store@example.com',
            website_url='https://example.com',
            messenger_ids={'telegram': 'asoud_store'},
        )
        StoreAccess.objects.create(user=self.buyer, market=self.market)
        self.client = APIClient()
        self.client.force_authenticate(self.buyer)

    def test_market_interactions_are_persisted_and_returned(self):
        base = f'/api/v1/storefront/markets/{self.market.id}'

        like = self.client.post(f'{base}/like')
        bookmark = self.client.post(f'{base}/bookmark')
        report = self.client.post(f'{base}/report', {'description': 'Incorrect store'})
        detail = self.client.get('/api/v1/storefront/markets', {'id': self.market.id})

        self.assertEqual(like.status_code, 200)
        self.assertTrue(like.data['is_liked'])
        self.assertEqual(bookmark.status_code, 200)
        self.assertTrue(bookmark.data['is_bookmarked'])
        self.assertEqual(report.status_code, 201)
        self.assertTrue(MarketLike.objects.get().is_active)
        self.assertTrue(MarketBookmark.objects.get().is_active)
        self.assertEqual(MarketReport.objects.get().description, 'Incorrect store')
        self.assertTrue(MarketView.objects.filter(user=self.buyer, market=self.market).exists())
        self.assertTrue(detail.data['data']['is_liked'])
        self.assertTrue(detail.data['data']['is_bookmarked'])
        self.assertEqual(detail.data['data']['likes_count'], 1)
        self.assertEqual(detail.data['data']['views_count'], 1)
        self.assertEqual(
            detail.data['data']['contact']['website_url'],
            'https://example.com',
        )
        self.assertEqual(detail.data['data']['contact']['fax'], '02112345679')

    def test_market_like_and_bookmark_are_toggles(self):
        base = f'/api/v1/storefront/markets/{self.market.id}'
        self.client.post(f'{base}/like')
        second_like = self.client.post(f'{base}/like')
        self.client.post(f'{base}/bookmark')
        second_bookmark = self.client.post(f'{base}/bookmark')

        self.assertFalse(second_like.data['is_liked'])
        self.assertEqual(second_like.data['likes_count'], 0)
        self.assertFalse(second_bookmark.data['is_bookmarked'])
