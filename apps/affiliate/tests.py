from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from apps.affiliate.models import AffiliateProduct, AffiliateProductTheme
from apps.category.models import Category, Group, SubCategory
from apps.market.models import Market
from apps.product.models import Product
from apps.users.models import User


class AffiliateOwnershipTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user('09125550001', None)
        self.source_owner = User.objects.create_user('09125550002', None)
        self.buyer = User.objects.create_user('09125550003', None)
        self.other_buyer = User.objects.create_user('09125550004', None)
        group = Group.objects.create(title='Affiliate group', market_fee=0)
        category = Category.objects.create(
            group=group,
            title='Affiliate category',
            market_fee=0,
        )
        self.subcategory = SubCategory.objects.create(
            category=category,
            title='Affiliate subcategory',
            market_fee=0,
        )
        self.market = self.create_market(self.owner, 'AFF-1')
        self.source_market = self.create_market(self.source_owner, 'AFF-2')
        self.source_product = self.create_product(
            self.source_market,
            'Source product',
            is_marketer=True,
        )
        self.unavailable_product = self.create_product(
            self.source_market,
            'Private product',
            is_marketer=False,
        )
        self.client = APIClient()

    def create_market(self, user, business_id):
        return Market.objects.create(
            user=user,
            type=Market.SHOP,
            status=Market.PUBLISHED,
            business_id=business_id,
            name=business_id,
            sub_category=self.subcategory,
        )

    def create_product(self, market, name, *, is_marketer):
        return Product.objects.create(
            market=market,
            type=Product.GOOD,
            name=name,
            description=f'{name} description',
            sub_category=self.subcategory,
            stock=10,
            main_price=Decimal('1000.000'),
            status=Product.PUBLISHED,
            sell_type=Product.ONLINE,
            ship_cost_pay_type=Product.FREE,
            is_marketer=is_marketer,
        )

    def payload(self, product=None, market=None):
        return {
            'market': str((market or self.market).id),
            'product': str((product or self.source_product).id),
            'sub_category': str(self.subcategory.id),
            'name': 'Affiliate listing',
            'stock': 5,
            'price': '1100.000',
            'status': AffiliateProduct.PUBLISHED,
            'sell_type': AffiliateProduct.ONLINE,
            'ship_cost_pay_type': AffiliateProduct.FREE,
        }

    def test_create_requires_owned_market_and_eligible_source_product(self):
        self.client.force_authenticate(self.owner)
        foreign_market = self.client.post(
            '/api/v1/user/affiliate/create/',
            self.payload(market=self.source_market),
            format='json',
        )
        unavailable = self.client.post(
            '/api/v1/user/affiliate/create/',
            self.payload(product=self.unavailable_product),
            format='json',
        )
        self.source_market.status = Market.DRAFT
        self.source_market.save(update_fields=['status', 'updated_at'])
        withdrawn_market = self.client.post(
            '/api/v1/user/affiliate/create/',
            self.payload(),
            format='json',
        )
        available = self.client.get('/api/v1/user/affiliate/products/')
        detail = self.client.get(
            f'/api/v1/user/affiliate/products/{self.source_product.id}'
        )

        self.assertEqual(foreign_market.status_code, 403)
        self.assertEqual(unavailable.status_code, 400)
        self.assertEqual(withdrawn_market.status_code, 400)
        self.assertNotIn(str(self.source_product.id), str(available.data))
        self.assertEqual(detail.status_code, 404)
        self.assertFalse(AffiliateProduct.objects.exists())

    def test_create_derives_source_identity_and_rejects_duplicate(self):
        self.client.force_authenticate(self.owner)
        payload = self.payload()
        payload['sub_category'] = str(
            SubCategory.objects.create(
                category=self.subcategory.category,
                title='Spoofed category',
                market_fee=0,
            ).id
        )

        first = self.client.post(
            '/api/v1/user/affiliate/create/',
            payload,
            format='json',
        )
        duplicate = self.client.post(
            '/api/v1/user/affiliate/create/',
            self.payload(),
            format='json',
        )

        self.assertEqual(first.status_code, 201)
        self.assertEqual(duplicate.status_code, 409)
        affiliate = AffiliateProduct.objects.get()
        self.assertEqual(affiliate.type, self.source_product.type)
        self.assertEqual(affiliate.sub_category, self.source_product.sub_category)
        self.assertEqual(affiliate.status, AffiliateProduct.DRAFT)
        update = self.client.put(
            f'/api/v1/user/affiliate/{affiliate.id}/update/',
            {'status': AffiliateProduct.PUBLISHED},
            format='json',
        )
        self.assertEqual(update.status_code, 200)
        affiliate.refresh_from_db()
        self.assertEqual(affiliate.status, AffiliateProduct.DRAFT)

    def test_list_and_detail_are_limited_to_owned_market(self):
        affiliate = AffiliateProduct.objects.create(
            market=self.market,
            product=self.source_product,
            type=self.source_product.type,
            name='Owned affiliate',
            sub_category=self.subcategory,
            stock=5,
            price=Decimal('1100.000'),
            status=AffiliateProduct.PUBLISHED,
            sell_type=AffiliateProduct.ONLINE,
            ship_cost_pay_type=AffiliateProduct.FREE,
        )
        self.client.force_authenticate(self.source_owner)

        listing = self.client.get(f'/api/v1/user/affiliate/list/{self.market.id}/')
        detail = self.client.get(f'/api/v1/user/affiliate/{affiliate.id}/')

        self.assertEqual(listing.status_code, 404)
        self.assertEqual(detail.status_code, 404)

    def test_theme_create_and_list_require_market_ownership(self):
        self.client.force_authenticate(self.source_owner)
        foreign_create = self.client.post(
            f'/api/v1/user/affiliate/theme/create/{self.market.id}/',
            {'name': 'Foreign theme', 'order': 1},
            format='json',
        )
        foreign_list = self.client.get(
            f'/api/v1/user/affiliate/theme/list/{self.market.id}/'
        )
        self.client.force_authenticate(self.owner)
        own_create = self.client.post(
            f'/api/v1/user/affiliate/theme/create/{self.market.id}/',
            {'name': 'Owned theme', 'order': 1},
            format='json',
        )

        self.assertEqual(foreign_create.status_code, 404)
        self.assertEqual(foreign_list.status_code, 404)
        self.assertEqual(own_create.status_code, 201)
        self.assertTrue(AffiliateProductTheme.objects.filter(market=self.market).exists())

    def test_source_withdrawal_blocks_cart_add_and_checkout(self):
        affiliate = AffiliateProduct.objects.create(
            market=self.market,
            product=self.source_product,
            type=self.source_product.type,
            name='Withdrawn source listing',
            sub_category=self.subcategory,
            stock=5,
            price=Decimal('1100.000'),
            status=AffiliateProduct.PUBLISHED,
            sell_type=AffiliateProduct.ONLINE,
            ship_cost_pay_type=AffiliateProduct.FREE,
        )
        self.client.force_authenticate(self.buyer)
        add = self.client.post(
            '/api/v1/user/order/add_item',
            {'affiliate_id': str(affiliate.id), 'quantity': 1},
            format='json',
        )
        self.assertEqual(add.status_code, 201)
        self.source_product.is_marketer = False
        self.source_product.save(update_fields=['is_marketer', 'updated_at'])

        checkout = self.client.post(
            '/api/v1/user/order/checkout',
            {'type': 'online', 'description': 'should fail'},
            format='json',
        )
        self.client.force_authenticate(self.other_buyer)
        blocked_add = self.client.post(
            '/api/v1/user/order/add_item',
            {'affiliate_id': str(affiliate.id), 'quantity': 1},
            format='json',
        )

        self.assertEqual(checkout.status_code, 400)
        self.assertEqual(blocked_add.status_code, 400)
