from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from apps.category.models import Category, Group, SubCategory
from apps.comment.models import Comment
from apps.market.models import Market
from apps.product.models import Product, ProductDiscount, ProductShipping, ProductTheme
from apps.product.serializers.owner_serializers import ProductCreateSerializer
from apps.users.models import User


class ProductShippingContractTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user('09128880001', None)
        self.other = User.objects.create_user('09128880002', None)
        group = Group.objects.create(title='Product group', market_fee=0)
        category = Category.objects.create(
            group=group,
            title='Product category',
            market_fee=0,
        )
        self.subcategory = SubCategory.objects.create(
            category=category,
            title='Product subcategory',
            market_fee=0,
        )
        self.market = Market.objects.create(
            user=self.owner,
            type=Market.SHOP,
            status=Market.PUBLISHED,
            business_id='PRODUCT-SHIP-1',
            name='Shipping market',
            sub_category=self.subcategory,
        )
        self.product = Product.objects.create(
            market=self.market,
            type=Product.GOOD,
            name='Product',
            sub_category=self.subcategory,
            stock=2,
            main_price=Decimal('1000.000'),
            status=Product.PUBLISHED,
            sell_type=Product.ONLINE,
            ship_cost_pay_type=Product.FREE,
        )
        self.client = APIClient()

    def test_product_create_rejects_customer_paid_shipping(self):
        serializer = ProductCreateSerializer(
            data={
                'market': str(self.market.id),
                'type': Product.GOOD,
                'name': 'New product',
                'sub_category': str(self.subcategory.id),
                'stock': 1,
                'main_price': '1000.000',
                'sell_type': Product.ONLINE,
                'ship_cost_pay_type': Product.CUSTOMER,
            }
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn('ship_cost_pay_type', serializer.errors)

    def test_legacy_product_discount_is_disabled_without_price_mutation(self):
        self.client.force_authenticate(self.owner)

        response = self.client.post(
            f'/api/v1/owner/product/discount/create/{self.product.id}/',
            {
                'users': [],
                'position': ProductDiscount.TOP_LEFT,
                'percentage': 50,
                'duration': 10,
            },
            format='json',
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(
            response.data['error']['code'],
            'legacy_product_discount_disabled',
        )
        self.product.refresh_from_db()
        self.assertEqual(self.product.main_price, Decimal('1000.000'))
        self.assertFalse(ProductDiscount.objects.exists())

    def test_theme_create_uses_server_owned_layout_name(self):
        self.client.force_authenticate(self.owner)

        response = self.client.post(
            f'/api/v1/owner/product/theme/create/{self.market.id}/',
            {'name': 'client-placeholder', 'order': 3},
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['data']['name'], 'layout-3')
        theme = ProductTheme.objects.get(market=self.market)
        self.assertEqual(theme.name, 'layout-3')
        self.assertEqual(theme.order, 3)

    def test_theme_update_rejects_product_from_another_owned_market(self):
        other_market = Market.objects.create(
            user=self.owner,
            type=Market.SHOP,
            status=Market.PUBLISHED,
            business_id='PRODUCT-THEME-2',
            name='Other theme market',
            sub_category=self.subcategory,
        )
        theme = ProductTheme.objects.create(
            market=other_market,
            name='layout-1',
            order=1,
        )
        self.client.force_authenticate(self.owner)

        response = self.client.put(
            f'/api/v1/owner/product/theme/update/{theme.id}/',
            {'product': self.product.id, 'index': 1},
            format='json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data['error']['code'],
            'product_theme_market_mismatch',
        )
        self.product.refresh_from_db()
        self.assertIsNone(self.product.theme_id)

    def test_theme_update_validates_slot_and_persists_same_market_product(self):
        theme = ProductTheme.objects.create(
            market=self.market,
            name='layout-2',
            order=2,
        )
        url = f'/api/v1/owner/product/theme/update/{theme.id}/'
        self.client.force_authenticate(self.owner)

        invalid = self.client.put(
            url,
            {'product': self.product.id, 'index': 5},
            format='json',
        )
        valid = self.client.put(
            url,
            {'product': self.product.id, 'index': 4},
            format='json',
        )

        self.assertEqual(invalid.status_code, 400)
        self.assertEqual(valid.status_code, 200)
        self.product.refresh_from_db()
        self.assertEqual(self.product.theme, theme)
        self.assertEqual(self.product.theme_index, '4')

    def test_shipping_create_is_explicitly_disabled_for_owner(self):
        self.client.force_authenticate(self.owner)

        response = self.client.post(
            f'/api/v1/owner/product/ship/create/{self.product.id}/',
            {'name': 'Courier', 'price': '250.00'},
            format='json',
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(
            response.data['error']['code'],
            'shipping_contract_unavailable',
        )
        self.assertFalse(ProductShipping.objects.exists())

    def test_legacy_shipping_list_is_owner_scoped_and_explicit(self):
        option = ProductShipping.objects.create(
            product=self.product,
            name='Legacy courier',
            price=Decimal('250.00'),
        )
        url = f'/api/v1/owner/product/ship/list/{self.product.id}/'
        self.client.force_authenticate(self.owner)
        owned = self.client.get(url)
        self.client.force_authenticate(self.other)
        foreign = self.client.get(url)

        self.assertEqual(owned.status_code, 200)
        self.assertEqual(owned.data['data'][0]['id'], str(option.id))
        self.assertEqual(owned.data['data'][0]['price'], '250.00')
        self.assertEqual(foreign.status_code, 403)

    def test_product_detail_uses_real_shipping_and_comment_relations(self):
        option = ProductShipping.objects.create(
            product=self.product,
            name='Legacy courier',
            price=Decimal('250.00'),
        )
        Comment.objects.create(
            content_object=self.product,
            creator=self.owner,
            content='Real comment',
        )

        self.client.force_authenticate(self.owner)
        response = self.client.get(
            f'/api/v1/owner/product/detail/{self.product.id}/'
        )
        data = response.data['data']

        self.assertEqual(response.status_code, 200)
        self.assertEqual(data['shipping_cost'][0]['id'], str(option.id))
        self.assertEqual(data['comments_count'], 1)
