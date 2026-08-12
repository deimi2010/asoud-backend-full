import json
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory

from django.test import TestCase, override_settings
from django.utils import timezone

from apps.cart.models import Order, OrderItem
from apps.category.models import Category, Group, SubCategory
from apps.market.models import Market
from apps.product.models import Product
from apps.users.models import User

from .models import AnalyticsDailyMetric, MLModelArtifact
from .services import ModelTrainer


class RealMLTrainingIntegrationTests(TestCase):
    def test_all_models_train_from_authoritative_non_empty_samples(self):
        group = Group.objects.create(title='ML group', market_fee=0)
        category = Category.objects.create(
            group=group,
            title='ML category',
            market_fee=0,
        )
        subcategory = SubCategory.objects.create(
            category=category,
            title='ML subcategory',
            market_fee=0,
        )
        owner = User.objects.create_user('09124440000', None)
        market = Market.objects.create(
            user=owner,
            type=Market.SHOP,
            status=Market.PUBLISHED,
            business_id='ML-TRAINING',
            name='ML training',
            sub_category=subcategory,
        )
        product = Product.objects.create(
            market=market,
            type=Product.GOOD,
            name='ML product',
            sub_category=subcategory,
            stock=100,
            main_price=Decimal('100.000'),
            status=Product.PUBLISHED,
            sell_type=Product.ONLINE,
            ship_cost_pay_type=Product.FREE,
        )

        for index in range(3):
            buyer = User.objects.create_user(f'0912444000{index + 1}', None)
            order = Order.objects.create(
                user=buyer,
                type=Order.ONLINE,
                status=Order.COMPLETED,
                is_paid=True,
                subtotal_amount=Decimal('100.000') * (index + 1),
                payable_amount=Decimal('100.000') * (index + 1),
            )
            OrderItem.objects.create(
                order=order,
                product=product,
                quantity=index + 1,
                unit_price=Decimal('100.000'),
            )

        today = timezone.localdate()
        for offset, units in enumerate([1, 2, 4, 7]):
            AnalyticsDailyMetric.objects.create(
                date=today - timedelta(days=3 - offset),
                scope=AnalyticsDailyMetric.PRODUCT,
                market=market,
                product=product,
                units_sold=units,
            )

        with TemporaryDirectory() as directory, override_settings(
            ANALYTICS_MODEL_DIR=directory,
        ):
            artifacts = ModelTrainer().train(
                ['recommender', 'demand', 'rfm'],
                activate_if_better=True,
            )
            payloads = {
                artifact.model_type: json.loads(Path(artifact.artifact_path).read_text())
                for artifact in artifacts
            }

        self.assertTrue(all(artifact.sample_count > 0 for artifact in artifacts))
        self.assertEqual(MLModelArtifact.objects.filter(is_active=True).count(), 3)
        self.assertTrue(payloads['recommender']['scores'])
        self.assertTrue(payloads['demand']['products'])
        self.assertTrue(payloads['rfm']['segments'])
