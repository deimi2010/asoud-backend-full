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

    def test_retry_with_same_client_request_id_is_idempotent(self):
        payload = self.create_payload(
            title='Summer sale',
            description='Market-wide discount',
            client_request_id='local-request-1',
        )
        first = self.client.post(
            '/api/v1/discount/owner/create/',
            payload,
            format='json',
        )
        second = self.client.post(
            '/api/v1/discount/owner/create/',
            payload,
            format='json',
        )

        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.data['data']['code'], second.data['data']['code'])
        self.assertEqual(Discount.objects.count(), 1)

    def test_market_list_is_filtered_and_contains_display_fields(self):
        other_market = Market.objects.create(
            user=self.owner,
            type=Market.SHOP,
            status=Market.PUBLISHED,
            business_id='DISCOUNT-2',
            name='Other market',
            sub_category=self.market.sub_category,
        )
        Discount.objects.create(
            content_object=self.market,
            owner=self.owner,
            title='Visible',
            description='Visible description',
            code='VISIBLE001',
            percentage=20,
            limitation=5,
        )
        Discount.objects.create(
            content_object=other_market,
            owner=self.owner,
            code='HIDDEN0001',
            percentage=10,
        )

        response = self.client.get(
            f'/api/v1/discount/owner/list/?market_id={self.market.id}'
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['data']), 1)
        item = response.data['data'][0]
        self.assertEqual(item['title'], 'Visible')
        self.assertEqual(item['remaining'], 5)
        self.assertEqual(item['status'], 'active')
        self.assertEqual(item['store_business_id'], self.market.business_id)

    def test_owner_can_deactivate_discount_and_it_cannot_validate(self):
        discount = Discount.objects.create(
            content_object=self.market,
            owner=self.owner,
            code='DISABLED01',
            percentage=10,
        )
        updated = self.client.patch(
            f'/api/v1/discount/owner/{discount.id}/',
            {'is_active': False},
            format='json',
        )
        self.client.force_authenticate(self.buyer)
        validated = self.client.post(
            '/api/v1/discount/user/validate/',
            {
                'code': discount.code,
                'content_type': 'market',
                'object_id': str(self.market.id),
            },
            format='json',
        )

        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.data['data']['status'], 'inactive')
        self.assertEqual(validated.status_code, 400)

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
