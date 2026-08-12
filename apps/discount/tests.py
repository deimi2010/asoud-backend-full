from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from apps.cart.models import Order
from apps.category.models import Category, Group, SubCategory
from apps.discount.models import Discount
from apps.market.models import Market
from apps.users.models import User


class DiscountOwnerIntegrityTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user('09122220001', None)
        self.other_owner = User.objects.create_user('09122220002', None)
        self.buyer = User.objects.create_user('09122220003', None)
        group = Group.objects.create(title='Discount group', market_fee=Decimal('0'))
        category = Category.objects.create(
            group=group,
            title='Discount category',
            market_fee=Decimal('0'),
        )
        subcategory = SubCategory.objects.create(
            category=category,
            title='Discount subcategory',
            market_fee=Decimal('0'),
        )
        self.market = Market.objects.create(
            user=self.owner,
            type=Market.SHOP,
            status=Market.PUBLISHED,
            business_id='DISCOUNT-1',
            name='Discount market',
            sub_category=subcategory,
        )
        self.client = APIClient()
        self.client.force_authenticate(self.owner)

    def create_payload(self, **overrides):
        payload = {
            'content_type': 'market',
            'object_id': str(self.market.id),
            'percentage': 10,
            'limitation': 5,
            'users': [],
        }
        payload.update(overrides)
        return payload

    def test_percentage_outside_business_range_is_rejected(self):
        response = self.client.post(
            '/api/v1/discount/owner/create/',
            self.create_payload(percentage=101),
            format='json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(Discount.objects.exists())

    def test_owner_cannot_create_discount_for_another_market(self):
        self.client.force_authenticate(self.other_owner)

        response = self.client.post(
            '/api/v1/discount/owner/create/',
            self.create_payload(),
            format='json',
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(Discount.objects.exists())

    def test_generated_code_is_unique_and_not_client_controlled(self):
        first = self.client.post(
            '/api/v1/discount/owner/create/',
            self.create_payload(code='CLIENT-CODE'),
            format='json',
        )
        second = self.client.post(
            '/api/v1/discount/owner/create/',
            self.create_payload(),
            format='json',
        )

        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 201)
        codes = list(Discount.objects.values_list('code', flat=True))
        self.assertEqual(len(set(codes)), 2)
        self.assertNotIn('CLIENT-CODE', codes)
        self.assertTrue(all(len(code) == 10 and code.isalnum() for code in codes))

    def test_discount_referenced_by_order_cannot_be_deleted(self):
        discount = Discount.objects.create(
            content_object=self.market,
            owner=self.owner,
            code='AUDITKEEP',
            percentage=10,
        )
        Order.objects.create(
            user=self.buyer,
            type=Order.ONLINE,
            status=Order.PENDING,
            discount=discount,
            discount_code_snapshot=discount.code,
        )

        response = self.client.delete(
            f'/api/v1/discount/owner/delete/{discount.id}/'
        )

        self.assertEqual(response.status_code, 409)
        self.assertTrue(Discount.objects.filter(id=discount.id).exists())

    def test_validation_counts_reserved_capacity(self):
        discount = Discount.objects.create(
            content_object=self.market,
            owner=self.owner,
            code='RESERVED10',
            percentage=10,
            limitation=1,
            reserved=1,
        )
        self.client.force_authenticate(self.buyer)

        response = self.client.post(
            '/api/v1/discount/user/validate/',
            {
                'code': discount.code.lower(),
                'content_type': 'market',
                'object_id': str(self.market.id),
            },
            format='json',
        )

        self.assertEqual(response.status_code, 400)
