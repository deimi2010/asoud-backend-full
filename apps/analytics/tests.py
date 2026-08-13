from datetime import timedelta
from decimal import Decimal
from tempfile import TemporaryDirectory

from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.cart.models import Order, OrderItem
from apps.category.models import Category, Group, SubCategory
from apps.market.models import Market
from apps.product.models import Product
from apps.referral.models import StoreAccess
from apps.users.models import User

from .models import AnalyticsDailyMetric, AnalyticsEvent, MLModelArtifact, UserSession
from .services import AnalyticsRecorder, AnalyticsService, DailyMetricBuilder, MLService


class AnalyticsV2Tests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user('09120000001', None)
        self.other_owner = User.objects.create_user('09120000002', None)
        self.buyer = User.objects.create_user('09120000003', None)
        self.other_buyer = User.objects.create_user('09120000004', None)
        self.staff = User.objects.create_user('09120000005', None, is_staff=True)
        group = Group.objects.create(title='Analytics group', market_fee=0)
        category = Category.objects.create(group=group, title='Analytics category', market_fee=0)
        self.subcategory = SubCategory.objects.create(
            category=category, title='Analytics subcategory', market_fee=0,
        )
        self.market = self.create_market(self.owner, 'ANALYTICS-1')
        self.other_market = self.create_market(self.other_owner, 'ANALYTICS-2')
        self.product = self.create_product(self.market, 'Product one', '100.000')
        self.similar = self.create_product(self.market, 'Product similar', '120.000')
        self.other_product = self.create_product(self.other_market, 'Other product', '900.000')
        StoreAccess.objects.create(user=self.buyer, market=self.market)
        self.client = APIClient()

    def create_market(self, owner, business_id):
        return Market.objects.create(
            user=owner,
            type=Market.SHOP,
            status=Market.PUBLISHED,
            business_id=business_id,
            name=business_id,
            sub_category=self.subcategory,
        )

    def create_product(self, market, name, price):
        return Product.objects.create(
            market=market,
            type=Product.GOOD,
            name=name,
            sub_category=self.subcategory,
            stock=20,
            main_price=Decimal(price),
            status=Product.PUBLISHED,
            sell_type=Product.ONLINE,
            ship_cost_pay_type=Product.FREE,
        )

    def create_paid_order(self, buyer, product, quantity=2, unit_price='100.000', payable='180.000'):
        with self.captureOnCommitCallbacks(execute=True):
            order = Order.objects.create(
                user=buyer,
                type=Order.ONLINE,
                status=Order.COMPLETED,
                is_paid=True,
                subtotal_amount=Decimal(unit_price) * quantity,
                payable_amount=Decimal(payable),
            )
        OrderItem.objects.create(
            order=order,
            product=product,
            quantity=quantity,
            unit_price=Decimal(unit_price),
        )
        return order

    def test_01_session_duration_is_derived(self):
        start = timezone.now()
        session = UserSession.objects.create(
            user=self.buyer,
            session_key='duration-session',
            started_at=start,
            ended_at=start + timedelta(minutes=30),
        )
        self.assertEqual(session.duration, timedelta(minutes=30))
        self.assertFalse(session.is_active)

    def test_02_event_uses_explicit_uuid_relations(self):
        event = AnalyticsRecorder.record(
            AnalyticsEvent.PRODUCT_VIEW,
            user=self.buyer,
            product=self.product,
            market=self.market,
        )
        self.assertEqual(event.product_id, self.product.id)
        self.assertEqual(event.market_id, self.market.id)

    def test_03_recorder_drops_financial_metadata(self):
        event = AnalyticsRecorder.record(
            AnalyticsEvent.ADD_TO_CART,
            user=self.buyer,
            product=self.product,
            metadata={'quantity': 2, 'amount': '999999', 'payment_status': 'paid'},
        )
        self.assertEqual(event.metadata, {'quantity': 2})

    def test_04_paid_order_signal_is_idempotent(self):
        order = self.create_paid_order(self.buyer, self.product)
        with self.captureOnCommitCallbacks(execute=True):
            order.save(update_fields=['updated_at'])
        self.assertEqual(
            AnalyticsEvent.objects.filter(event_type=AnalyticsEvent.PAID_ORDER, order=order).count(),
            1,
        )

    def test_05_platform_revenue_uses_payable_amount(self):
        self.create_paid_order(self.buyer, self.product, unit_price='100.000', payable='180.000')
        AnalyticsRecorder.record(
            AnalyticsEvent.PRODUCT_VIEW,
            user=self.buyer,
            product=self.product,
            metadata={'amount': '999999.000'},
        )
        dashboard = AnalyticsService().dashboard()
        self.assertEqual(dashboard['gross_revenue'], '180.000')

    def test_06_dashboard_has_explicit_refund_disclaimer(self):
        dashboard = AnalyticsService().dashboard()
        self.assertFalse(dashboard['refunds_deducted'])
        self.assertIn('refunds are not deducted', dashboard['gross_revenue_disclaimer'])

    def test_07_owner_dashboard_is_tenant_scoped(self):
        self.create_paid_order(self.buyer, self.product, payable='200.000')
        self.create_paid_order(self.other_buyer, self.other_product, unit_price='900.000', payable='1800.000')
        dashboard = AnalyticsService().dashboard(market_ids=[self.market.id])
        self.assertEqual(dashboard['gross_revenue'], '200.000')
        self.assertEqual(dashboard['paid_orders'], 1)

    def test_08_platform_dashboard_is_staff_only(self):
        self.client.force_authenticate(self.owner)
        forbidden = self.client.get('/api/v1/analytics/platform/dashboard/')
        self.client.force_authenticate(self.staff)
        allowed = self.client.get('/api/v1/analytics/platform/dashboard/')
        self.assertEqual(forbidden.status_code, 403)
        self.assertEqual(allowed.status_code, 200)

    def test_09_owner_summary_is_accessible_and_scoped(self):
        self.create_paid_order(self.buyer, self.product, unit_price='100.000', payable='180.000')
        self.client.force_authenticate(self.owner)
        response = self.client.get('/api/v1/analytics/owner/summary/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['gross_revenue'], '200.000')
        self.assertFalse(response.data['refunds_deducted'])

    def test_10_time_series_has_authoritative_daily_shape(self):
        self.create_paid_order(self.buyer, self.product, payable='180.000')
        rows = AnalyticsService().time_series(days=7)
        self.assertEqual(len(rows), 7)
        self.assertIn('gross_revenue', rows[-1])
        self.assertFalse(rows[-1]['refunds_deducted'])

    def test_11_daily_metric_builder_uses_paid_snapshots(self):
        self.create_paid_order(self.buyer, self.product, quantity=3, unit_price='100.000', payable='270.000')
        AnalyticsRecorder.record(
            AnalyticsEvent.PRODUCT_VIEW,
            user=self.buyer,
            product=self.product,
            market=self.market,
        )
        today = timezone.localdate()
        DailyMetricBuilder().rebuild(today, today)
        metric = AnalyticsDailyMetric.objects.get(scope=AnalyticsDailyMetric.PLATFORM, date=today)
        self.assertEqual(metric.units_sold, 3)
        self.assertEqual(metric.gross_revenue, Decimal('270.000'))

    def test_12_recommendations_support_uuid_products(self):
        AnalyticsRecorder.record(
            AnalyticsEvent.PRODUCT_VIEW,
            user=self.buyer,
            product=self.product,
            market=self.market,
        )
        recommendations = MLService().get_product_recommendations(self.buyer, 5)
        self.assertTrue(any(item['id'] == str(self.similar.id) for item in recommendations))

    def test_13_similar_products_are_real_published_products(self):
        similar = MLService().get_similar_products(self.product, 5)
        ids = {item['id'] for item in similar}
        self.assertIn(str(self.similar.id), ids)
        self.assertNotIn(str(self.product.id), ids)

    def test_14_demand_forecast_is_deterministic_from_paid_units(self):
        today = timezone.localdate()
        for index, units in enumerate([1, 2, 3, 4]):
            AnalyticsDailyMetric.objects.create(
                date=today - timedelta(days=3 - index),
                scope=AnalyticsDailyMetric.PRODUCT,
                product=self.product,
                market=self.market,
                units_sold=units,
            )
        first = MLService().demand_forecast(self.product, 3)
        second = MLService().demand_forecast(self.product, 3)
        self.assertEqual(first, second)
        self.assertEqual(len(first['forecast']), 3)

    def test_15_raw_events_are_staff_read_only(self):
        AnalyticsRecorder.record(AnalyticsEvent.LOGIN, user=self.buyer)
        self.client.force_authenticate(self.staff)
        listed = self.client.get('/api/v1/analytics/platform/events/')
        posted = self.client.post('/api/v1/analytics/platform/events/', {}, format='json')
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(posted.status_code, 405)

    def test_16_product_detail_generates_server_event(self):
        self.client.force_authenticate(self.buyer)
        response = self.client.get('/api/v1/storefront/products', {'id': self.product.id})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(AnalyticsEvent.objects.filter(
            user=self.buyer,
            product=self.product,
            event_type=AnalyticsEvent.PRODUCT_VIEW,
        ).exists())

    def test_17_cart_add_event_cannot_set_financial_fields(self):
        self.client.force_authenticate(self.buyer)
        response = self.client.post(
            '/api/v1/user/order/add_item',
            {'product_id': str(self.product.id), 'quantity': 1, 'amount': '0.001'},
            format='json',
        )
        self.assertEqual(response.status_code, 201)
        event = AnalyticsEvent.objects.get(event_type=AnalyticsEvent.ADD_TO_CART)
        self.assertEqual(event.metadata, {'quantity': 1})

    def test_18_training_command_creates_versioned_active_artifacts(self):
        with TemporaryDirectory() as directory, override_settings(ANALYTICS_MODEL_DIR=directory):
            call_command(
                'train_analytics_models',
                models=['recommender', 'demand', 'rfm'],
                activate_if_better=True,
                verbosity=0,
            )
        self.assertEqual(MLModelArtifact.objects.count(), 3)
        self.assertEqual(MLModelArtifact.objects.filter(is_active=True).count(), 3)
