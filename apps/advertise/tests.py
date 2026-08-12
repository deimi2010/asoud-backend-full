from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from apps.advertise.core import AdvertisementCore
from apps.advertise.models import Advertisement
from apps.category.models import Category, Group, SubCategory
from apps.market.models import Market
from apps.product.models import Product
from apps.users.models import User


class AdvertisementIntegrityTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user('09124440001', None)
        self.other_owner = User.objects.create_user('09124440002', None)
        group = Group.objects.create(title='Advertisement group', market_fee=0)
        self.category = Category.objects.create(
            group=group,
            title='Advertisement category',
            market_fee=0,
        )
        self.subcategory = SubCategory.objects.create(
            category=self.category,
            title='Advertisement subcategory',
            market_fee=0,
        )
        self.market = self.create_market(self.owner, 'ADV-1')
        self.other_market = self.create_market(self.other_owner, 'ADV-2')
        self.product = self.create_product(self.market, 'Product one')
        self.second_product = self.create_product(self.market, 'Product two')
        self.product.colleague_price = Decimal('777.000')
        self.product.marketer_price = Decimal('888.000')
        self.product.maximum_sell_price = Decimal('999.000')
        self.product.save(
            update_fields=[
                'colleague_price',
                'marketer_price',
                'maximum_sell_price',
                'updated_at',
            ]
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

    def create_product(self, market, name):
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
        )

    def create_advertisement(self, user=None, **overrides):
        data = {
            'user': user or self.owner,
            'type': Advertisement.GOOD,
            'name': 'Advertisement',
            'description': 'Description',
            'category': self.category,
            'price': Decimal('1000.000'),
        }
        data.update(overrides)
        return Advertisement.objects.create(**data)

    def test_manual_create_and_payment_fail_closed(self):
        self.client.force_authenticate(self.owner)

        create = self.client.post(
            '/api/v1/advertisements/create',
            {
                'type': Advertisement.GOOD,
                'name': 'Free paid ad',
                'description': 'attempt',
                'is_paid': True,
            },
            format='json',
        )
        payment = self.client.get('/api/v1/advertisements/payment')

        self.assertEqual(create.status_code, 503)
        self.assertEqual(payment.status_code, 503)
        self.assertFalse(Advertisement.objects.exists())

    def test_public_list_and_detail_hide_unpaid_advertisements(self):
        unpaid = self.create_advertisement()
        paid = self.create_advertisement(
            user=self.other_owner,
            name='Paid advertisement',
            is_paid=True,
        )
        paid_product = self.create_advertisement(
            product=self.product,
            name=self.product.name,
            is_paid=True,
        )

        listing = self.client.get('/api/v1/advertisements/')
        hidden_detail = self.client.get(f'/api/v1/advertisements/{unpaid.id}')
        paid_detail = self.client.get(f'/api/v1/advertisements/{paid.id}')
        legacy_hidden = self.client.get(f'/advertisements?id={unpaid.id}')
        legacy_product = self.client.get(f'/advertisements?id={paid_product.id}')

        self.assertEqual(listing.status_code, 200)
        self.assertIn(str(paid.id), str(listing.data))
        self.assertNotIn(str(unpaid.id), str(listing.data))
        self.assertEqual(hidden_detail.status_code, 404)
        self.assertEqual(paid_detail.status_code, 200)
        self.assertEqual(legacy_hidden.status_code, 404)
        self.assertEqual(legacy_product.status_code, 200)
        self.assertNotIn(self.other_owner.mobile_number, str(paid_detail.data))
        self.assertNotIn('colleague_price', str(legacy_product.data))
        self.assertNotIn('marketer_price', str(legacy_product.data))
        self.assertNotIn('maximum_sell_price', str(legacy_product.data))
        self.market.status = Market.DRAFT
        self.market.save(update_fields=['status', 'updated_at'])
        self.assertEqual(
            self.client.get(f'/advertisements?id={paid_product.id}').status_code,
            404,
        )

    def test_update_and_delete_are_owner_scoped(self):
        advertisement = self.create_advertisement()
        self.client.force_authenticate(self.other_owner)

        update = self.client.put(
            f'/api/v1/advertisements/{advertisement.id}/update',
            {'name': 'stolen'},
            format='json',
        )
        delete = self.client.delete(
            f'/api/v1/advertisements/{advertisement.id}/delete'
        )

        self.assertEqual(update.status_code, 404)
        self.assertEqual(delete.status_code, 404)
        advertisement.refresh_from_db()
        self.assertEqual(advertisement.name, 'Advertisement')

    def test_update_cannot_self_activate_or_replace_product(self):
        advertisement = self.create_advertisement()
        self.client.force_authenticate(self.owner)
        activation = self.client.put(
            f'/api/v1/advertisements/{advertisement.id}/update',
            {'name': 'Edited', 'is_paid': True},
            format='json',
        )
        replacement = self.client.put(
            f'/api/v1/advertisements/{advertisement.id}/update',
            {'product': str(self.second_product.id)},
            format='json',
        )

        self.assertEqual(activation.status_code, 200)
        self.assertEqual(replacement.status_code, 400)
        advertisement.refresh_from_db()
        self.assertEqual(advertisement.name, 'Edited')
        self.assertFalse(advertisement.is_paid)
        self.assertIsNone(advertisement.product)

    def test_product_advertisement_is_authoritative_unpaid_and_idempotent(self):
        first = AdvertisementCore.create_advertisement_for_product(self.product)
        second = AdvertisementCore.create_advertisement_for_product(self.product)

        advertisement = Advertisement.objects.get(product=self.product)
        self.assertEqual(first['id'], second['id'])
        self.assertEqual(Advertisement.objects.filter(product=self.product).count(), 1)
        self.assertEqual(advertisement.user, self.owner)
        self.assertFalse(advertisement.is_paid)
        self.assertEqual(advertisement.name, self.product.name)
        self.assertEqual(advertisement.price, self.product.main_price)

        self.client.force_authenticate(self.owner)
        update = self.client.put(
            f'/api/v1/advertisements/{advertisement.id}/update',
            {'name': 'detached'},
            format='json',
        )
        delete = self.client.delete(
            f'/api/v1/advertisements/{advertisement.id}/delete'
        )
        self.assertEqual(update.status_code, 409)
        self.assertEqual(delete.status_code, 409)
        self.assertTrue(Advertisement.objects.filter(id=advertisement.id).exists())

        self.assertEqual(
            self.client.get(f'/api/v1/advertisements/{advertisement.id}').status_code,
            404,
        )
