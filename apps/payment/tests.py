from decimal import Decimal
from unittest.mock import Mock, patch

from django.contrib.contenttypes.models import ContentType
from django.test import RequestFactory, TestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from apps.cart.models import Order, OrderItem
from apps.cart.views.owner import OrderVerifyView
from apps.category.models import Category, Group, SubCategory
from apps.market.models import Market, MarketContact, MarketLocation
from apps.payment.core import PaymentCore, PostPaymentCore
from apps.payment.models import Payment, Zarinpal
from apps.payment.serializers.user import PaymentCreateSerializer
from apps.product.models import Product
from apps.region.models import City, Country, Province
from apps.users.models import User
from apps.wallet.models import Wallet


def create_test_product(owner, suffix):
    group = Group.objects.create(title=f'Group {suffix}', market_fee=0)
    category = Category.objects.create(
        group=group,
        title=f'Category {suffix}',
        market_fee=0,
    )
    subcategory = SubCategory.objects.create(
        category=category,
        title=f'Subcategory {suffix}',
        market_fee=0,
    )
    market = Market.objects.create(
        user=owner,
        type=Market.SHOP,
        status=Market.PUBLISHED,
        is_paid=True,
        business_id=f'PAY-{suffix}',
        name=f'Market {suffix}',
        sub_category=subcategory,
    )
    return Product.objects.create(
        market=market,
        type=Product.GOOD,
        name=f'Product {suffix}',
        sub_category=subcategory,
        stock=10,
        main_price=Decimal('1500.000'),
        status=Product.PUBLISHED,
        sell_type=Product.ONLINE,
        ship_cost_pay_type=Product.FREE,
    )


class PaymentCreateSecurityTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('09120000011', None)
        self.other_user = User.objects.create_user('09120000012', None)
        self.wallet = Wallet.objects.create(user=self.user)
        self.foreign_wallet = Wallet.objects.create(user=self.other_user)
        self.request = RequestFactory().post('/payments/create/')
        self.request.user = self.user
        self.product = create_test_product(self.user, 'create')

    def serializer(self, **overrides):
        data = {
            'amount': '1000',
            'target': 'wallet',
            'target_id': str(self.wallet.id),
            'gateway': 'zarinpal',
        }
        data.update(overrides)
        return PaymentCreateSerializer(data=data, context={'request': self.request})

    def test_wallet_top_up_must_target_the_authenticated_users_wallet(self):
        serializer = self.serializer(target_id=str(self.foreign_wallet.id))

        self.assertFalse(serializer.is_valid())
        self.assertIn('target_id', serializer.errors)

    def test_unsupported_target_is_rejected(self):
        serializer = self.serializer(target='advertisement')

        self.assertFalse(serializer.is_valid())
        self.assertIn('target', serializer.errors)

    def test_fractional_gateway_amount_is_rejected(self):
        serializer = self.serializer(amount='1000.5')

        self.assertFalse(serializer.is_valid())
        self.assertIn('amount', serializer.errors)

    def test_store_subscription_amount_is_server_authoritative(self):
        market = self.product.market
        market.status = Market.DRAFT
        market.sub_category.market_fee = Decimal('2500')
        market.sub_category.save(update_fields=['market_fee', 'updated_at'])
        market.save(update_fields=['status', 'updated_at'])
        MarketContact.objects.create(
            market=market,
            first_mobile_number=self.user.mobile_number,
        )
        country = Country.objects.create(name='Iran payment')
        province = Province.objects.create(country=country, name='Tehran payment')
        city = City.objects.create(province=province, name='Tehran payment')
        MarketLocation.objects.create(
            market=market,
            city=city,
            address='Payment address',
            zip_code='1234567890',
            latitude='35.000000',
            longitude='51.000000',
        )

        wrong = self.serializer(
            target='market_subscription', target_id=str(market.id), amount='1'
        )
        correct = self.serializer(
            target='market_subscription', target_id=str(market.id), amount='2500'
        )

        self.assertFalse(wrong.is_valid())
        self.assertIn('amount', wrong.errors)
        self.assertTrue(correct.is_valid(), correct.errors)
        without_client_amount = self.serializer(
            target='market_subscription',
            target_id=str(market.id),
        )
        without_client_amount.initial_data.pop('amount')
        self.assertTrue(without_client_amount.is_valid(), without_client_amount.errors)

    def test_completed_subscription_marks_store_paid_without_requesting_publication(self):
        market = self.product.market
        market.status = Market.DRAFT
        market.is_paid = False
        market.save(update_fields=['status', 'is_paid', 'updated_at'])
        payment = Payment.objects.create(
            user=self.user,
            amount=Decimal('2500'),
            target_content_type=ContentType.objects.get_for_model(Market),
            target_id=market.id,
        )

        PostPaymentCore(self.user).payment_process(payment)

        market.refresh_from_db()
        self.assertEqual(market.status, Market.DRAFT)
        self.assertTrue(market.is_paid)

    def test_gateway_amount_cannot_exceed_transaction_column_capacity(self):
        serializer = self.serializer(amount='1000000000000000000')

        self.assertFalse(serializer.is_valid())
        self.assertIn('amount', serializer.errors)

    @patch.object(OrderItem, 'total_price', return_value=Decimal('1500.000'))
    def test_order_amount_is_derived_and_client_mismatch_is_rejected(self, _):
        order = Order.objects.create(
            user=self.user,
            type=Order.ONLINE,
            status=Order.PENDING,
            is_paid=False,
        )
        OrderItem.objects.create(order=order, product=self.product, quantity=1)

        serializer = self.serializer(
            amount='1',
            target='order',
            target_id=str(order.id),
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn('amount', serializer.errors)

    @patch.object(OrderItem, 'total_price', return_value=Decimal('1500.000'))
    def test_order_payment_must_belong_to_authenticated_user(self, _):
        order = Order.objects.create(
            user=self.other_user,
            type=Order.ONLINE,
            status=Order.PENDING,
            is_paid=False,
        )
        OrderItem.objects.create(order=order, product=self.product, quantity=1)

        serializer = self.serializer(
            amount='1500',
            target='order',
            target_id=str(order.id),
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn('target_id', serializer.errors)

    @patch.dict('os.environ', {'ZARINPAL_MERCHANT_ID': 'test-merchant'})
    @patch('apps.payment.core.requests.post')
    def test_payment_session_uses_validated_target_and_amount(self, post):
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {'data': {'authority': 'authority-1'}}
        post.return_value = response
        serializer = self.serializer(amount='2500')
        self.assertTrue(serializer.is_valid(), serializer.errors)

        success, gateway = PaymentCore().pay(self.user, serializer.validated_data)

        self.assertTrue(success)
        payment = gateway.payment
        self.assertEqual(payment.user, self.user)
        self.assertEqual(payment.target_id, self.wallet.id)
        self.assertEqual(payment.amount, 2500)
        self.assertEqual(payment.status, Payment.PENDING)
        _, kwargs = post.call_args
        self.assertEqual(kwargs['json']['amount'], 2500)
        self.assertEqual(kwargs['timeout'], PaymentCore.request_timeout)

    @patch.object(OrderItem, 'total_price', return_value=Decimal('1500.000'))
    @patch.dict('os.environ', {'ZARINPAL_MERCHANT_ID': 'test-merchant'})
    @patch('apps.payment.core.requests.post')
    @patch('apps.payment.core.reserve_order_inventory')
    def test_duplicate_order_request_reuses_one_gateway_session(self, reserve, post, _):
        order = Order.objects.create(
            user=self.user,
            type=Order.ONLINE,
            status=Order.PENDING,
            is_paid=False,
        )
        OrderItem.objects.create(order=order, product=self.product, quantity=1)
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {'data': {'authority': 'order-authority'}}

        def provider_request(**kwargs):
            order.refresh_from_db()
            self.assertEqual(order.status, Order.PROCESSING)
            return response

        post.side_effect = provider_request

        first_serializer = self.serializer(
            amount='1500',
            target='order',
            target_id=str(order.id),
        )
        self.assertTrue(first_serializer.is_valid(), first_serializer.errors)
        first_success, first_gateway = PaymentCore().pay(
            self.user,
            first_serializer.validated_data,
        )

        second_serializer = self.serializer(
            amount='1500',
            target='order',
            target_id=str(order.id),
        )
        self.assertTrue(second_serializer.is_valid(), second_serializer.errors)
        second_success, second_gateway = PaymentCore().pay(
            self.user,
            second_serializer.validated_data,
        )

        self.assertTrue(first_success)
        self.assertTrue(second_success)
        self.assertEqual(first_gateway.id, second_gateway.id)
        self.assertEqual(post.call_count, 1)
        self.assertEqual(Payment.objects.filter(target_id=order.id).count(), 1)
        order.refresh_from_db()
        self.assertEqual(order.status, Order.PROCESSING)


class PaymentVerificationSecurityTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('09120000021', None)
        self.wallet = Wallet.objects.create(user=self.user)
        self.product = create_test_product(self.user, 'verify')

    def create_pending_payment(self, amount=1000, authority='authority-pending'):
        payment = Payment.objects.create(
            user=self.user,
            amount=amount,
            target_content_type=ContentType.objects.get_for_model(Wallet),
            target_id=self.wallet.id,
            gateway_content_type=ContentType.objects.get_for_model(Zarinpal),
            status=Payment.PENDING,
        )
        Zarinpal.objects.create(
            payment=payment,
            authority=authority,
            verification_data={'integrity_version': PaymentCore.integrity_version},
        )
        return payment

    def test_completed_callback_is_idempotent_without_calling_gateway_again(self):
        payment = Payment.objects.create(
            user=self.user,
            amount=1000,
            target_content_type=ContentType.objects.get_for_model(Wallet),
            target_id=self.wallet.id,
            gateway_content_type=ContentType.objects.get_for_model(Zarinpal),
            status=Payment.COMPLETE,
        )
        Zarinpal.objects.create(
            payment=payment,
            authority='authority-complete',
            transaction_id='reference-1',
        )
        request = RequestFactory().get(
            '/payments/verify/',
            {'Authority': 'authority-complete', 'Status': 'OK'},
        )

        with patch('apps.payment.core.requests.post') as post:
            success, message = PaymentCore().verify(request)

        self.assertTrue(success)
        self.assertEqual(message, 'Payment already processed')
        post.assert_not_called()
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, 0)

    @patch.dict('os.environ', {'ZARINPAL_MERCHANT_ID': 'test-merchant'})
    @patch('apps.payment.core.requests.post')
    def test_legacy_pending_session_is_not_processed(self, post):
        payment = Payment.objects.create(
            user=self.user,
            amount=1000,
            target_content_type=ContentType.objects.get_for_model(Wallet),
            target_id=self.wallet.id,
            gateway_content_type=ContentType.objects.get_for_model(Zarinpal),
            status=Payment.PENDING,
        )
        Zarinpal.objects.create(payment=payment, authority='legacy-authority')
        request = RequestFactory().get(
            '/payments/verify/',
            {'Authority': 'legacy-authority', 'Status': 'OK'},
        )

        success, message = PaymentCore().verify(request)

        self.assertFalse(success)
        self.assertIn('Legacy payment session', message)
        post.assert_not_called()
        payment.refresh_from_db()
        self.wallet.refresh_from_db()
        self.assertEqual(payment.status, Payment.PENDING)
        self.assertEqual(self.wallet.balance, 0)

    @patch.dict('os.environ', {'ZARINPAL_MERCHANT_ID': 'test-merchant'})
    @patch('apps.payment.core.requests.post')
    def test_successful_callback_credits_wallet_exactly_once(self, post):
        payment = self.create_pending_payment()
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            'data': {'code': 100, 'ref_id': 12345, 'amount': 1000}
        }
        post.return_value = response
        request = RequestFactory().get(
            '/payments/verify/',
            {'Authority': 'authority-pending', 'Status': 'OK'},
        )

        first_success, _ = PaymentCore().verify(request)
        second_success, second_message = PaymentCore().verify(request)

        self.assertTrue(first_success)
        self.assertTrue(second_success)
        self.assertEqual(second_message, 'Payment already processed')
        self.assertEqual(post.call_count, 1)
        payment.refresh_from_db()
        self.wallet.refresh_from_db()
        self.assertEqual(payment.status, Payment.COMPLETE)
        self.assertEqual(self.wallet.balance, 1000)
        self.assertEqual(self.user.wallet_transactions.count(), 1)

    @patch.dict('os.environ', {'ZARINPAL_MERCHANT_ID': 'test-merchant'})
    @patch('apps.payment.core.requests.post')
    def test_gateway_amount_mismatch_fails_without_crediting_wallet(self, post):
        payment = self.create_pending_payment(authority='authority-mismatch')
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            'data': {'code': 100, 'ref_id': 12346, 'amount': 1}
        }
        post.return_value = response
        request = RequestFactory().get(
            '/payments/verify/',
            {'Authority': 'authority-mismatch', 'Status': 'OK'},
        )

        success, message = PaymentCore().verify(request)

        self.assertFalse(success)
        self.assertEqual(message, 'Payment amount mismatch requires reconciliation')
        payment.refresh_from_db()
        self.wallet.refresh_from_db()
        self.assertEqual(payment.status, Payment.PENDING)
        self.assertEqual(self.wallet.balance, 0)
        self.assertFalse(self.user.wallet_transactions.exists())

    @patch.dict('os.environ', {'ZARINPAL_MERCHANT_ID': 'test-merchant'})
    @patch('apps.payment.core.requests.post')
    @patch('apps.payment.core.confirm_order_inventory')
    def test_order_callback_completes_snapshot_despite_later_price_change(self, confirm, post):
        order = Order.objects.create(
            user=self.user,
            type=Order.ONLINE,
            status=Order.PROCESSING,
            is_paid=False,
        )
        OrderItem.objects.create(order=order, product=self.product, quantity=1)
        payment = Payment.objects.create(
            user=self.user,
            amount=1500,
            target_content_type=ContentType.objects.get_for_model(Order),
            target_id=order.id,
            gateway_content_type=ContentType.objects.get_for_model(Zarinpal),
            status=Payment.PENDING,
        )
        Zarinpal.objects.create(
            payment=payment,
            authority='order-callback',
            verification_data={'integrity_version': PaymentCore.integrity_version},
        )
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            'data': {'code': 100, 'ref_id': 12347, 'amount': 1500}
        }
        post.return_value = response
        request = RequestFactory().get(
            '/payments/verify/',
            {'Authority': 'order-callback', 'Status': 'OK'},
        )

        with patch.object(OrderItem, 'total_price', return_value=Decimal('9999.000')):
            success, _ = PaymentCore().verify(request)

        self.assertTrue(success)
        order.refresh_from_db()
        payment.refresh_from_db()
        self.assertTrue(order.is_paid)
        self.assertEqual(order.status, Order.COMPLETED)
        self.assertEqual(payment.status, Payment.COMPLETE)

    @patch.dict('os.environ', {'ZARINPAL_MERCHANT_ID': 'test-merchant'})
    @patch('apps.payment.core.requests.post')
    def test_ambiguous_order_amount_keeps_session_locked_for_reconciliation(self, post):
        order = Order.objects.create(
            user=self.user,
            type=Order.ONLINE,
            status=Order.PROCESSING,
            is_paid=False,
        )
        OrderItem.objects.create(order=order, product=self.product, quantity=1)
        payment = Payment.objects.create(
            user=self.user,
            amount=1500,
            target_content_type=ContentType.objects.get_for_model(Order),
            target_id=order.id,
            gateway_content_type=ContentType.objects.get_for_model(Zarinpal),
            status=Payment.PENDING,
        )
        Zarinpal.objects.create(
            payment=payment,
            authority='order-ambiguous',
            verification_data={'integrity_version': PaymentCore.integrity_version},
        )
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            'data': {'code': 100, 'ref_id': 12348, 'amount': 1}
        }
        post.return_value = response
        request = RequestFactory().get(
            '/payments/verify/',
            {'Authority': 'order-ambiguous', 'Status': 'OK'},
        )

        success, message = PaymentCore().verify(request)

        self.assertFalse(success)
        self.assertIn('requires reconciliation', message)
        order.refresh_from_db()
        payment.refresh_from_db()
        self.assertEqual(order.status, Order.PROCESSING)
        self.assertFalse(order.is_paid)
        self.assertEqual(payment.status, Payment.PENDING)

    @patch.dict('os.environ', {'ZARINPAL_MERCHANT_ID': 'test-merchant'})
    @patch('apps.payment.core.requests.post')
    def test_definitive_gateway_rejection_releases_order(self, post):
        order = Order.objects.create(
            user=self.user,
            type=Order.ONLINE,
            status=Order.PROCESSING,
            is_paid=False,
        )
        OrderItem.objects.create(order=order, product=self.product, quantity=1)
        payment = Payment.objects.create(
            user=self.user,
            amount=1500,
            target_content_type=ContentType.objects.get_for_model(Order),
            target_id=order.id,
            gateway_content_type=ContentType.objects.get_for_model(Zarinpal),
            status=Payment.PENDING,
        )
        Zarinpal.objects.create(
            payment=payment,
            authority='order-rejected',
            verification_data={'integrity_version': PaymentCore.integrity_version},
        )
        replacement_order = Order.objects.create(
            user=self.user,
            type=Order.ONLINE,
            status=Order.DRAFT,
            is_paid=False,
        )
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {'data': {'code': -51}}
        post.return_value = response
        request = RequestFactory().get(
            '/payments/verify/',
            {'Authority': 'order-rejected', 'Status': 'OK'},
        )

        success, _ = PaymentCore().verify(request)

        self.assertFalse(success)
        order.refresh_from_db()
        payment.refresh_from_db()
        self.assertEqual(order.status, Order.FAILED)
        self.assertEqual(payment.status, Payment.FAILED)
        self.assertEqual(Order.get_or_create_order(self.user), replacement_order)


class WalletOrderPaymentSecurityTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('09120000031', None)
        self.wallet = Wallet.objects.create(user=self.user, balance=2000)
        self.product = create_test_product(self.user, 'wallet')
        self.order = Order.objects.create(
            user=self.user,
            type=Order.ONLINE,
            status=Order.PENDING,
            is_paid=False,
        )
        OrderItem.objects.create(order=self.order, product=self.product, quantity=1)

    @patch.object(OrderItem, 'total_price', return_value=Decimal('1500.000'))
    @patch('apps.payment.core.confirm_order_inventory')
    @patch('apps.payment.core.reserve_order_inventory')
    def test_wallet_order_payment_debits_before_completing_order(self, reserve, confirm, _):
        success, _ = PostPaymentCore(self.user).wallet_process(
            'order',
            self.order.id,
            Decimal('1500.000'),
            self.wallet.id,
        )

        self.assertTrue(success)
        self.wallet.refresh_from_db()
        self.order.refresh_from_db()
        self.assertEqual(self.wallet.balance, 500)
        self.assertTrue(self.order.is_paid)
        self.assertEqual(self.order.status, Order.COMPLETED)
        self.assertEqual(self.user.wallet_transactions.count(), 1)

    @patch.object(OrderItem, 'total_price', return_value=Decimal('1500.000'))
    def test_wallet_order_payment_rejects_client_amount_without_side_effects(self, _):
        success, message = PostPaymentCore(self.user).wallet_process(
            'order',
            self.order.id,
            Decimal('1.000'),
            self.wallet.id,
        )

        self.assertFalse(success)
        self.assertIn('does not match', message)
        self.wallet.refresh_from_db()
        self.order.refresh_from_db()
        self.assertEqual(self.wallet.balance, 2000)
        self.assertFalse(self.order.is_paid)
        self.assertEqual(self.order.status, Order.PENDING)
        self.assertFalse(self.user.wallet_transactions.exists())


class OwnerOrderTransitionLockTests(TestCase):
    @patch('apps.cart.views.owner.Order.objects')
    @patch('apps.cart.views.owner._is_exclusively_owned_order', return_value=True)
    def test_owner_cannot_overwrite_processing_order(self, ownership, order_objects):
        owner = User.objects.create_user('09120000041', None)
        locked_order = Mock()
        locked_order.status = Order.PROCESSING
        order_objects.select_for_update.return_value.get.return_value = locked_order
        request = APIRequestFactory().put(
            '/owner/orders/verify/',
            {
                'id': '00000000-0000-0000-0000-000000000041',
                'verified': True,
                'description': 'approved',
            },
            format='json',
        )
        force_authenticate(request, user=owner)

        response = OrderVerifyView.as_view()(request)

        self.assertEqual(response.status_code, 400)
        order_objects.select_for_update.assert_called_once_with()
        locked_order.save.assert_not_called()
