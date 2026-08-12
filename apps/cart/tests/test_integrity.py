from decimal import Decimal
from unittest.mock import Mock, patch

from requests.exceptions import Timeout
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.test.client import RequestFactory
from rest_framework.test import APIClient

from apps.affiliate.models import AffiliateProduct
from apps.cart.models import Order
from apps.cart.services import (
    CartIntegrityError,
    confirm_order_inventory,
    release_order_inventory,
    reserve_order_inventory,
)
from apps.category.models import Category, Group, SubCategory
from apps.discount.models import Discount
from apps.market.models import Market
from apps.product.models import Product
from apps.users.models import User
from apps.payment.core import (
    PaymentCore,
    PostPaymentCore,
    reconcile_stale_payment_sessions,
)
from apps.payment.models import Payment
from apps.wallet.models import Wallet


class CartIntegrityTests(TestCase):
    def setUp(self):
        self.buyer = User.objects.create_user('09121110001', None)
        self.owner = User.objects.create_user('09121110002', None)
        self.other_owner = User.objects.create_user('09121110003', None)
        group = Group.objects.create(title='Group', market_fee=0)
        category = Category.objects.create(group=group, title='Category', market_fee=0)
        self.subcategory = SubCategory.objects.create(
            category=category,
            title='Subcategory',
            market_fee=0,
        )
        self.market = self.create_market(self.owner, 'M-1')
        self.other_market = self.create_market(self.other_owner, 'M-2')
        self.product = self.create_product(self.market, 'Product 1', 5, '1000.000')
        self.other_product = self.create_product(
            self.other_market,
            'Product 2',
            5,
            '2000.000',
        )
        self.client = APIClient()
        self.client.force_authenticate(self.buyer)

    def create_market(self, owner, business_id):
        return Market.objects.create(
            user=owner,
            type=Market.SHOP,
            status=Market.PUBLISHED,
            is_paid=True,
            business_id=business_id,
            name=business_id,
            sub_category=self.subcategory,
        )

    def create_product(self, market, name, stock, price):
        return Product.objects.create(
            market=market,
            type=Product.GOOD,
            name=name,
            sub_category=self.subcategory,
            stock=stock,
            main_price=Decimal(price),
            status=Product.PUBLISHED,
            sell_type=Product.ONLINE,
            ship_cost_pay_type=Product.FREE,
        )

    def add_product(self, product, quantity=1):
        return self.client.post(
            '/api/v1/user/order/add_item',
            {'product_id': str(product.id), 'quantity': quantity},
            format='json',
        )

    def checkout(self, **overrides):
        data = {'type': Order.ONLINE, 'description': 'placed'}
        data.update(overrides)
        return self.client.post('/api/v1/user/order/checkout', data, format='json')

    def test_user_order_detail_update_and_delete_accept_only_the_owner(self):
        own_order = Order.objects.create(
            user=self.buyer,
            status=Order.DRAFT,
            description='original',
        )

        detail = self.client.get(f'/api/v1/user/order/{own_order.id}')
        updated = self.client.put(
            f'/api/v1/user/order/{own_order.id}/update',
            {'description': 'updated'},
            format='json',
        )
        deleted = self.client.delete(f'/api/v1/user/order/{own_order.id}/delete')

        self.assertEqual(detail.status_code, 200)
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.data['data']['description'], 'updated')
        self.assertEqual(deleted.status_code, 204)
        self.assertFalse(Order.objects.filter(id=own_order.id).exists())

    def test_user_order_mutations_hide_cross_user_orders(self):
        other_buyer = User.objects.create_user('09121110004', None)
        foreign_order = Order.objects.create(
            user=other_buyer,
            status=Order.DRAFT,
            description='foreign',
        )

        detail = self.client.get(f'/api/v1/user/order/{foreign_order.id}')
        updated = self.client.put(
            f'/api/v1/user/order/{foreign_order.id}/update',
            {'description': 'stolen'},
            format='json',
        )
        deleted = self.client.delete(f'/api/v1/user/order/{foreign_order.id}/delete')

        self.assertEqual(detail.status_code, 404)
        self.assertEqual(updated.status_code, 404)
        self.assertEqual(deleted.status_code, 404)
        foreign_order.refresh_from_db()
        self.assertEqual(foreign_order.description, 'foreign')

    def test_user_order_detail_rejects_anonymous_requests(self):
        own_order = Order.objects.create(user=self.buyer, status=Order.DRAFT)
        self.client.force_authenticate(user=None)

        response = self.client.get(f'/api/v1/user/order/{own_order.id}')

        self.assertEqual(response.status_code, 401)

    def test_checkout_freezes_price_and_opens_a_new_draft_cart(self):
        self.assertEqual(self.add_product(self.product, 2).status_code, 201)

        response = self.checkout()

        self.assertEqual(response.status_code, 200)
        placed = Order.objects.get(user=self.buyer, status=Order.PENDING)
        self.assertEqual(placed.subtotal_amount, Decimal('2000.000'))
        self.assertEqual(placed.payable_amount, Decimal('2000.000'))
        self.product.main_price = Decimal('9000.000')
        self.product.save(update_fields=['main_price', 'updated_at'])
        self.assertEqual(placed.total_price(), Decimal('2000.000'))

        self.client.get('/api/v1/user/order/orders')
        self.assertTrue(Order.objects.filter(user=self.buyer, status=Order.DRAFT).exists())

    def test_cart_rejects_items_from_a_second_market(self):
        self.assertEqual(self.add_product(self.product).status_code, 201)

        response = self.add_product(self.other_product)

        self.assertEqual(response.status_code, 400)
        order = Order.objects.get(user=self.buyer, status=Order.DRAFT)
        self.assertEqual(order.items.count(), 1)

    def test_customer_paid_shipping_fails_closed_before_and_after_cart_add(self):
        self.product.ship_cost_pay_type = Product.CUSTOMER
        self.product.save(update_fields=['ship_cost_pay_type', 'updated_at'])

        rejected_add = self.add_product(self.product)

        self.assertEqual(rejected_add.status_code, 400)
        self.assertEqual(
            rejected_add.data['error']['code'],
            'shipping_contract_unavailable',
        )

        self.product.ship_cost_pay_type = Product.FREE
        self.product.save(update_fields=['ship_cost_pay_type', 'updated_at'])
        self.assertEqual(self.add_product(self.product).status_code, 201)
        self.product.ship_cost_pay_type = Product.CUSTOMER
        self.product.save(update_fields=['ship_cost_pay_type', 'updated_at'])

        rejected_checkout = self.checkout()

        self.assertEqual(rejected_checkout.status_code, 400)
        self.assertEqual(
            rejected_checkout.data['error']['code'],
            'shipping_contract_unavailable',
        )
        order = Order.objects.get(user=self.buyer, status=Order.DRAFT)
        self.assertIsNone(order.payable_amount)

    def test_affiliate_shipping_rejects_customer_paid_listing_or_source(self):
        affiliate = AffiliateProduct.objects.create(
            market=self.market,
            product=self.product,
            type=Product.GOOD,
            name='Affiliate shipping product',
            sub_category=self.subcategory,
            stock=5,
            price=Decimal('1100.000'),
            status=AffiliateProduct.PUBLISHED,
            sell_type=AffiliateProduct.ONLINE,
            ship_cost_pay_type=AffiliateProduct.CUSTOMER,
        )

        listing_rejected = self.client.post(
            '/api/v1/user/order/add_item',
            {'affiliate_id': str(affiliate.id), 'quantity': 1},
            format='json',
        )
        affiliate.ship_cost_pay_type = AffiliateProduct.FREE
        affiliate.save(update_fields=['ship_cost_pay_type', 'updated_at'])
        self.product.ship_cost_pay_type = Product.CUSTOMER
        self.product.is_marketer = True
        self.product.save(
            update_fields=['ship_cost_pay_type', 'is_marketer', 'updated_at']
        )
        source_rejected = self.client.post(
            '/api/v1/user/order/add_item',
            {'affiliate_id': str(affiliate.id), 'quantity': 1},
            format='json',
        )

        self.assertEqual(listing_rejected.status_code, 400)
        self.assertEqual(source_rejected.status_code, 400)
        self.assertEqual(
            listing_rejected.data['error']['code'],
            'shipping_contract_unavailable',
        )
        self.assertEqual(
            source_rejected.data['error']['code'],
            'shipping_contract_unavailable',
        )

    def test_discount_and_stock_reservation_are_idempotent_and_releasable(self):
        discount = Discount.objects.create(
            content_object=self.market,
            owner=self.owner,
            code='SAVE10',
            percentage=10,
            limitation=1,
        )
        self.add_product(self.product, 2)
        self.assertEqual(self.checkout(discount_code=discount.code).status_code, 200)
        order = Order.objects.get(user=self.buyer, status=Order.PENDING)
        self.assertEqual(order.discount_amount, Decimal('200.000'))
        self.assertEqual(order.payable_amount, Decimal('1800.000'))

        reserve_order_inventory(order)
        reserve_order_inventory(order)
        self.product.refresh_from_db()
        discount.refresh_from_db()
        self.assertEqual(self.product.stock, 3)
        self.assertEqual(discount.reserved, 1)

        release_order_inventory(order)
        release_order_inventory(order)
        self.product.refresh_from_db()
        discount.refresh_from_db()
        self.assertEqual(self.product.stock, 5)
        self.assertEqual(discount.reserved, 0)

    def test_stale_order_instances_cannot_double_apply_inventory_transitions(self):
        self.add_product(self.product, 1)
        self.checkout()
        order = Order.objects.get(user=self.buyer, status=Order.PENDING)
        first = Order.objects.get(id=order.id)
        stale = Order.objects.get(id=order.id)

        reserve_order_inventory(first)
        reserve_order_inventory(stale)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 4)

        first = Order.objects.get(id=order.id)
        stale = Order.objects.get(id=order.id)
        release_order_inventory(first, terminal=False)
        release_order_inventory(stale, terminal=False)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 5)

        reserve_order_inventory(Order.objects.get(id=order.id))
        first = Order.objects.get(id=order.id)
        stale = Order.objects.get(id=order.id)
        confirm_order_inventory(first)
        confirm_order_inventory(stale)
        self.product.refresh_from_db()
        order.refresh_from_db()
        self.assertEqual(self.product.stock, 4)
        self.assertEqual(order.inventory_status, Order.INVENTORY_CONFIRMED)

    def test_confirmation_consumes_discount_without_double_decrementing_stock(self):
        discount = Discount.objects.create(
            content_object=self.product,
            owner=self.owner,
            code='PRODUCT25',
            percentage=25,
            limitation=2,
        )
        self.add_product(self.product, 1)
        self.checkout(discount_code=discount.code)
        order = Order.objects.get(user=self.buyer, status=Order.PENDING)

        reserve_order_inventory(order)
        confirm_order_inventory(order)
        confirm_order_inventory(order)

        self.product.refresh_from_db()
        discount.refresh_from_db()
        order.refresh_from_db()
        self.assertEqual(self.product.stock, 4)
        self.assertEqual(discount.reserved, 0)
        self.assertEqual(discount.consumed, 1)
        self.assertEqual(order.inventory_status, Order.INVENTORY_CONFIRMED)

    def test_wallet_payment_reserves_stock_and_confirms_the_order(self):
        wallet = Wallet.objects.create(user=self.buyer, balance=Decimal('5000'))
        self.add_product(self.product, 2)
        self.checkout()
        order = Order.objects.get(user=self.buyer, status=Order.PENDING)

        success, _ = PostPaymentCore(self.buyer).wallet_process(
            'order',
            order.id,
            order.total_price(),
            wallet.id,
        )

        self.assertTrue(success)
        wallet.refresh_from_db()
        self.product.refresh_from_db()
        order.refresh_from_db()
        self.assertEqual(wallet.balance, 3000)
        self.assertEqual(self.product.stock, 3)
        self.assertEqual(order.status, Order.COMPLETED)
        self.assertEqual(order.inventory_status, Order.INVENTORY_CONFIRMED)

    def test_failed_wallet_debit_releases_reservations_for_retry(self):
        wallet = Wallet.objects.create(user=self.buyer, balance=Decimal('100'))
        discount = Discount.objects.create(
            content_object=self.market,
            owner=self.owner,
            code='RETRY10',
            percentage=10,
            limitation=1,
        )
        self.add_product(self.product, 1)
        self.checkout(discount_code=discount.code)
        order = Order.objects.get(user=self.buyer, status=Order.PENDING)

        success, _ = PostPaymentCore(self.buyer).wallet_process(
            'order',
            order.id,
            order.total_price(),
            wallet.id,
        )

        self.assertFalse(success)
        self.product.refresh_from_db()
        discount.refresh_from_db()
        order.refresh_from_db()
        self.assertEqual(self.product.stock, 5)
        self.assertEqual(discount.reserved, 0)
        self.assertEqual(order.inventory_status, Order.INVENTORY_NONE)
        self.assertEqual(order.status, Order.PENDING)

    def test_owner_accepting_cash_order_atomically_consumes_stock(self):
        self.add_product(self.product, 2)
        self.checkout(type=Order.CASH)
        order = Order.objects.get(user=self.buyer, status=Order.PENDING)
        self.client.force_authenticate(self.owner)

        response = self.client.put(
            '/api/v1/owner/order/verify',
            {'id': str(order.id), 'verified': True, 'description': 'cash accepted'},
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        self.product.refresh_from_db()
        order.refresh_from_db()
        self.assertEqual(self.product.stock, 3)
        self.assertEqual(order.status, Order.COMPLETED)
        self.assertTrue(order.is_paid)
        self.assertEqual(order.inventory_status, Order.INVENTORY_CONFIRMED)

    @patch.dict('os.environ', {'ZARINPAL_MERCHANT_ID': 'test-merchant'})
    @patch('apps.payment.core.requests.post')
    def test_gateway_success_keeps_one_stock_decrement_and_confirms_discount(self, post):
        discount = Discount.objects.create(
            content_object=self.market,
            owner=self.owner,
            code='GATEWAY10',
            percentage=10,
            limitation=1,
        )
        self.add_product(self.product, 1)
        self.checkout(discount_code=discount.code)
        order = Order.objects.get(user=self.buyer, status=Order.PENDING)
        create_response = Mock()
        create_response.raise_for_status.return_value = None
        create_response.json.return_value = {'data': {'authority': 'inventory-authority'}}
        post.return_value = create_response

        success, _ = PaymentCore().pay(
            self.buyer,
            {'resolved_target': order, 'resolved_amount': order.total_price()},
        )
        self.assertTrue(success)
        self.product.refresh_from_db()
        order.refresh_from_db()
        self.assertEqual(self.product.stock, 4)
        self.assertEqual(order.inventory_status, Order.INVENTORY_RESERVED)

        verify_response = Mock()
        verify_response.raise_for_status.return_value = None
        verify_response.json.return_value = {
            'data': {'code': 100, 'ref_id': 9001, 'amount': 900}
        }
        post.return_value = verify_response
        request = RequestFactory().get(
            '/api/v1/user/payments/verify/',
            {'Authority': 'inventory-authority', 'Status': 'OK'},
        )
        verified, _ = PaymentCore().verify(request)

        self.assertTrue(verified)
        self.product.refresh_from_db()
        discount.refresh_from_db()
        order.refresh_from_db()
        self.assertEqual(self.product.stock, 4)
        self.assertEqual(discount.reserved, 0)
        self.assertEqual(discount.consumed, 1)
        self.assertEqual(order.inventory_status, Order.INVENTORY_CONFIRMED)
        self.assertEqual(order.status, Order.COMPLETED)

    @patch.dict('os.environ', {'ZARINPAL_MERCHANT_ID': 'test-merchant'})
    @patch('apps.payment.core.requests.post')
    def test_gateway_creation_failure_releases_stock(self, post):
        self.add_product(self.product, 2)
        self.checkout()
        order = Order.objects.get(user=self.buyer, status=Order.PENDING)
        post.side_effect = Timeout('timeout')

        success, _ = PaymentCore().pay(
            self.buyer,
            {'resolved_target': order, 'resolved_amount': order.total_price()},
        )

        self.assertFalse(success)
        self.product.refresh_from_db()
        order.refresh_from_db()
        self.assertEqual(self.product.stock, 5)
        self.assertEqual(order.inventory_status, Order.INVENTORY_RELEASED)
        self.assertEqual(order.status, Order.FAILED)

    @patch.dict('os.environ', {'ZARINPAL_MERCHANT_ID': 'test-merchant'})
    @patch('apps.payment.core.requests.post')
    def test_stale_gateway_reconciliation_releases_only_definitive_failure(self, post):
        self.add_product(self.product, 2)
        self.checkout()
        order = Order.objects.get(user=self.buyer, status=Order.PENDING)
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {'data': {'authority': 'stale-authority'}}
        rejected = Mock()
        rejected.raise_for_status.return_value = None
        rejected.json.return_value = {'data': {'code': -51}}
        post.side_effect = [response, rejected]
        success, gateway = PaymentCore().pay(
            self.buyer,
            {'resolved_target': order, 'resolved_amount': order.total_price()},
        )
        self.assertTrue(success)
        Payment.objects.filter(id=gateway.payment_id).update(
            created_at='2000-01-01T00:00:00Z'
        )

        result = reconcile_stale_payment_sessions(limit=10)

        gateway.payment.refresh_from_db()
        order.refresh_from_db()
        self.product.refresh_from_db()
        self.assertEqual(gateway.payment.status, Payment.FAILED)
        self.assertEqual(order.status, Order.FAILED)
        self.assertEqual(order.inventory_status, Order.INVENTORY_RELEASED)
        self.assertEqual(self.product.stock, 5)
        self.assertEqual(result['released'], 1)

    @patch.dict('os.environ', {'ZARINPAL_MERCHANT_ID': 'test-merchant'})
    @patch('apps.payment.core.requests.post')
    def test_stale_gateway_reconciliation_keeps_ambiguous_reservation(self, post):
        self.add_product(self.product, 1)
        self.checkout()
        order = Order.objects.get(user=self.buyer, status=Order.PENDING)
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {'data': {'authority': 'ambiguous-authority'}}
        post.side_effect = [response, Timeout('gateway unavailable')]
        success, gateway = PaymentCore().pay(
            self.buyer,
            {'resolved_target': order, 'resolved_amount': order.total_price()},
        )
        self.assertTrue(success)
        Payment.objects.filter(id=gateway.payment_id).update(
            created_at='2000-01-01T00:00:00Z'
        )

        result = reconcile_stale_payment_sessions(limit=10)

        gateway.payment.refresh_from_db()
        order.refresh_from_db()
        self.product.refresh_from_db()
        self.assertEqual(gateway.payment.status, Payment.PENDING)
        self.assertEqual(order.status, Order.PROCESSING)
        self.assertEqual(order.inventory_status, Order.INVENTORY_RESERVED)
        self.assertEqual(self.product.stock, 4)
        self.assertEqual(result['ambiguous'], 1)

    def test_database_rejects_order_item_with_two_targets(self):
        affiliate = AffiliateProduct.objects.create(
            market=self.market,
            product=self.product,
            type=AffiliateProduct.GOOD if hasattr(AffiliateProduct, 'GOOD') else Product.GOOD,
            name='Affiliate product',
            sub_category=self.subcategory,
            stock=5,
            price=Decimal('1100.000'),
            status=AffiliateProduct.PUBLISHED,
            sell_type=AffiliateProduct.ONLINE,
            ship_cost_pay_type=AffiliateProduct.FREE,
        )
        order = Order.objects.create(user=self.buyer, status=Order.PENDING)

        with self.assertRaises(IntegrityError), transaction.atomic():
            order.items.create(
                product=self.product,
                affiliate=affiliate,
                quantity=1,
            )

    def test_affiliate_delete_requires_ownership_and_preserves_order_history(self):
        affiliate = AffiliateProduct.objects.create(
            market=self.market,
            product=self.product,
            type=Product.GOOD,
            name='Protected affiliate',
            sub_category=self.subcategory,
            stock=5,
            price=Decimal('1100.000'),
            status=AffiliateProduct.PUBLISHED,
            sell_type=AffiliateProduct.ONLINE,
            ship_cost_pay_type=AffiliateProduct.FREE,
        )
        order = Order.objects.create(user=self.buyer, status=Order.PENDING)
        order.items.create(affiliate=affiliate, quantity=1)
        url = f'/api/v1/user/affiliate/{affiliate.id}/delete/'
        update_url = f'/api/v1/user/affiliate/{affiliate.id}/update/'

        self.client.force_authenticate(self.other_owner)
        self.assertEqual(
            self.client.put(update_url, {'stock': 0}, format='json').status_code,
            404,
        )
        self.assertEqual(self.client.delete(url).status_code, 404)
        self.client.force_authenticate(self.owner)
        self.assertEqual(
            self.client.put(
                update_url,
                {'market': str(self.other_market.id)},
                format='json',
            ).status_code,
            400,
        )
        self.assertEqual(self.client.delete(url).status_code, 409)
        affiliate.refresh_from_db()
        self.assertTrue(AffiliateProduct.objects.filter(id=affiliate.id).exists())
        self.assertEqual(affiliate.stock, 5)
        self.assertEqual(affiliate.market, self.market)
        self.assertEqual(order.items.count(), 1)

    def test_post_checkout_item_mutation_fails_closed(self):
        self.add_product(self.product, 1)
        self.checkout()
        order = Order.objects.get(user=self.buyer, status=Order.PENDING)
        item = order.items.get()
        item.quantity = 2
        item.save(update_fields=['quantity', 'updated_at'])

        with self.assertRaises(CartIntegrityError) as caught:
            reserve_order_inventory(order)

        self.assertEqual(caught.exception.code, 'order_changed')
        self.product.refresh_from_db()
        order.refresh_from_db()
        self.assertEqual(self.product.stock, 5)
        self.assertEqual(order.inventory_status, Order.INVENTORY_NONE)

    def test_legacy_mixed_market_order_is_hidden_from_each_owner(self):
        order = Order.objects.create(
            user=self.buyer,
            type=Order.ONLINE,
            status=Order.PENDING,
        )
        order.items.create(product=self.product, quantity=1, unit_price=self.product.main_price)
        order.items.create(
            product=self.other_product,
            quantity=1,
            unit_price=self.other_product.main_price,
        )
        self.client.force_authenticate(self.owner)

        listing = self.client.get('/api/v1/owner/order/list')
        detail = self.client.get(f'/api/v1/owner/order/{order.id}')
        verify = self.client.put(
            '/api/v1/owner/order/verify',
            {'id': str(order.id), 'verified': True, 'description': 'should fail'},
            format='json',
        )

        self.assertEqual(listing.status_code, 200)
        self.assertNotIn(str(order.id), str(listing.data))
        self.assertEqual(detail.status_code, 403)
        self.assertEqual(verify.status_code, 403)
