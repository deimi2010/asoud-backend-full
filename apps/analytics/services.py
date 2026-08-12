"""Truthful analytics aggregation, recommendation, and model training services."""

import hashlib
import json
import os
import uuid
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.db.models import (
    Count, DecimalField, ExpressionWrapper, F, Q, Sum,
)
from django.db.models.functions import Coalesce
from django.utils import timezone

from apps.cart.models import Order, OrderItem
from apps.market.models import Market
from apps.product.models import Product

from .models import AnalyticsDailyMetric, AnalyticsEvent, MLModelArtifact, UserSession


GROSS_REVENUE_DISCLAIMER = 'Gross paid revenue; refunds are not deducted.'
SAFE_METADATA_KEYS = {'source', 'quantity', 'bookmarked', 'device'}


def _money(value):
    return Decimal(value or 0).quantize(Decimal('0.001'))


class AnalyticsRecorder:
    """Creates allowlisted, server-side events with no financial authority."""

    @staticmethod
    def session_key_for_request(request):
        user = getattr(request, 'user', None)
        auth = getattr(request, 'auth', None)
        if user and user.is_authenticated and auth:
            digest = hashlib.sha256(f'{user.pk}:{auth}'.encode()).hexdigest()
            return digest[:64]
        session = getattr(request, 'session', None)
        if session is not None:
            if not session.session_key:
                session.create()
            return session.session_key[:64]
        return uuid.uuid4().hex

    @classmethod
    def record_request(cls, request, event_type, **relations):
        user = request.user if getattr(request, 'user', None) and request.user.is_authenticated else None
        session_key = cls.session_key_for_request(request)
        session, _ = UserSession.objects.get_or_create(
            session_key=session_key,
            defaults={'user': user},
        )
        if user and session.user_id != user.pk:
            session.user = user
        session.last_seen_at = timezone.now()
        session.save(update_fields=['user', 'last_seen_at', 'updated_at'])
        return cls.record(
            event_type,
            user=user,
            session=session,
            session_key=session_key,
            **relations,
        )

    @staticmethod
    def record(event_type, *, user=None, session=None, session_key='', metadata=None,
               product=None, market=None, order=None, dedupe_key=None, occurred_at=None):
        allowed = {choice[0] for choice in AnalyticsEvent.EVENT_TYPES}
        if event_type not in allowed:
            raise ValueError('Unsupported analytics event type')
        safe_metadata = {
            key: value for key, value in (metadata or {}).items()
            if key in SAFE_METADATA_KEYS
        }
        values = {
            'user': user,
            'session': session,
            'session_key': session_key,
            'event_type': event_type,
            'product': product,
            'market': market,
            'order': order,
            'metadata': safe_metadata,
            'occurred_at': occurred_at or timezone.now(),
        }
        if dedupe_key:
            event, _ = AnalyticsEvent.objects.get_or_create(
                dedupe_key=dedupe_key,
                defaults=values,
            )
            return event
        return AnalyticsEvent.objects.create(**values)


class AnalyticsService:
    """Read-only metrics calculated from authoritative operational tables."""

    @staticmethod
    def period(days=30, end=None):
        end = end or timezone.now()
        return end - timedelta(days=max(1, min(int(days), 366))), end

    @staticmethod
    def _item_market_filter(market_ids):
        return Q(product__market_id__in=market_ids) | Q(affiliate__market_id__in=market_ids)

    def dashboard(self, *, days=30, market_ids=None):
        start, end = self.period(days)
        orders = Order.objects.filter(is_paid=True, created_at__gte=start, created_at__lt=end)
        items = OrderItem.objects.filter(order__in=orders)
        events = AnalyticsEvent.objects.filter(occurred_at__gte=start, occurred_at__lt=end)

        if market_ids is not None:
            market_ids = list(market_ids)
            items = items.filter(self._item_market_filter(market_ids))
            orders = orders.filter(items__in=items).distinct()
            events = events.filter(market_id__in=market_ids)
            gross_expression = ExpressionWrapper(
                F('unit_price') * F('quantity'),
                output_field=DecimalField(max_digits=18, decimal_places=3),
            )
            gross_revenue = items.aggregate(value=Sum(gross_expression))['value']
        else:
            gross_revenue = orders.aggregate(value=Sum('payable_amount'))['value']

        product_views = events.filter(event_type=AnalyticsEvent.PRODUCT_VIEW)
        unique_viewers = product_views.filter(user__isnull=False).values('user_id').distinct().count()
        unique_buyers = orders.values('user_id').distinct().count()
        conversion_rate = (unique_buyers / unique_viewers * 100) if unique_viewers else 0.0

        return {
            'period': {'start': start.isoformat(), 'end': end.isoformat(), 'days': int(days)},
            'paid_orders': orders.count(),
            'units_sold': items.aggregate(value=Coalesce(Sum('quantity'), 0))['value'],
            'unique_buyers': unique_buyers,
            'authenticated_unique_product_viewers': unique_viewers,
            'product_views': product_views.count(),
            'add_to_cart_count': events.filter(event_type=AnalyticsEvent.ADD_TO_CART).count(),
            'conversion_rate': round(conversion_rate, 2),
            'gross_revenue': str(_money(gross_revenue)),
            'refunds_deducted': False,
            'gross_revenue_disclaimer': GROSS_REVENUE_DISCLAIMER,
        }

    def time_series(self, *, days=30, market_ids=None):
        _, end = self.period(days)
        result = []
        for offset in range(int(days) - 1, -1, -1):
            day = (end - timedelta(days=offset)).date()
            next_day = day + timedelta(days=1)
            orders = Order.objects.filter(is_paid=True, created_at__date=day)
            items = OrderItem.objects.filter(order__in=orders)
            if market_ids is not None:
                items = items.filter(self._item_market_filter(list(market_ids)))
                orders = orders.filter(items__in=items).distinct()
                amount = items.aggregate(value=Sum(ExpressionWrapper(
                    F('unit_price') * F('quantity'),
                    output_field=DecimalField(max_digits=18, decimal_places=3),
                )))['value']
            else:
                amount = orders.aggregate(value=Sum('payable_amount'))['value']
            result.append({
                'date': day.isoformat(),
                'paid_orders': orders.count(),
                'units_sold': items.aggregate(value=Coalesce(Sum('quantity'), 0))['value'],
                'gross_revenue': str(_money(amount)),
                'refunds_deducted': False,
                'gross_revenue_disclaimer': GROSS_REVENUE_DISCLAIMER,
            })
        return result

    def top_products(self, *, days=30, market_ids=None, limit=10):
        start, end = self.period(days)
        items = OrderItem.objects.filter(
            order__is_paid=True,
            order__created_at__gte=start,
            order__created_at__lt=end,
        )
        if market_ids is not None:
            items = items.filter(self._item_market_filter(list(market_ids)))
        rows = (
            items.annotate(canonical_product_id=Coalesce('product_id', 'affiliate__product_id'))
            .values('canonical_product_id')
            .annotate(
                units_sold=Sum('quantity'),
                gross_revenue=Sum(ExpressionWrapper(
                    F('unit_price') * F('quantity'),
                    output_field=DecimalField(max_digits=18, decimal_places=3),
                )),
            )
            .order_by('-units_sold')[:limit]
        )
        products = Product.objects.in_bulk([row['canonical_product_id'] for row in rows])
        return [
            {
                'product_id': str(row['canonical_product_id']),
                'name': products[row['canonical_product_id']].name,
                'units_sold': row['units_sold'],
                'gross_revenue': str(_money(row['gross_revenue'])),
            }
            for row in rows if row['canonical_product_id'] in products
        ]

    def top_markets(self, *, days=30, limit=10):
        start, end = self.period(days)
        rows = (
            OrderItem.objects.filter(
                order__is_paid=True,
                order__created_at__gte=start,
                order__created_at__lt=end,
            )
            .annotate(canonical_market_id=Coalesce('product__market_id', 'affiliate__market_id'))
            .values('canonical_market_id')
            .annotate(
                units_sold=Sum('quantity'),
                paid_orders=Count('order_id', distinct=True),
                gross_revenue=Sum(ExpressionWrapper(
                    F('unit_price') * F('quantity'),
                    output_field=DecimalField(max_digits=18, decimal_places=3),
                )),
            )
            .order_by('-gross_revenue')[:limit]
        )
        markets = Market.objects.in_bulk([row['canonical_market_id'] for row in rows])
        return [
            {
                'market_id': str(row['canonical_market_id']),
                'name': markets[row['canonical_market_id']].name,
                'units_sold': row['units_sold'],
                'paid_orders': row['paid_orders'],
                'gross_revenue': str(_money(row['gross_revenue'])),
            }
            for row in rows if row['canonical_market_id'] in markets
        ]


class MLService:
    """Self-scoped recommendations and deterministic, evidence-backed forecasts."""

    @staticmethod
    def _product_payload(products):
        return [
            {
                'id': str(product.id),
                'name': product.name,
                'market_id': str(product.market_id),
                'main_price': str(product.main_price),
            }
            for product in products
        ]

    def get_product_recommendations(self, user, limit=10):
        limit = max(1, min(int(limit), 50))
        interacted_ids = list(
            AnalyticsEvent.objects.filter(
                user=user,
                product__isnull=False,
                event_type__in=[AnalyticsEvent.PRODUCT_VIEW, AnalyticsEvent.ADD_TO_CART],
            ).order_by('-occurred_at').values_list('product_id', flat=True)[:100]
        )
        purchased_ids = list(
            OrderItem.objects.filter(order__user=user, order__is_paid=True)
            .annotate(canonical_product_id=Coalesce('product_id', 'affiliate__product_id'))
            .values_list('canonical_product_id', flat=True)
        )
        seed_ids = interacted_ids + purchased_ids
        seed_categories = Product.objects.filter(id__in=seed_ids).values_list('sub_category_id', flat=True)
        candidates = Product.objects.filter(
            status=Product.PUBLISHED,
            market__status=Market.PUBLISHED,
        ).exclude(id__in=purchased_ids)
        if seed_ids:
            candidates = candidates.filter(sub_category_id__in=seed_categories)
        candidates = candidates.annotate(
            paid_units=Coalesce(Sum(
                'orderitem__quantity',
                filter=Q(orderitem__order__is_paid=True),
            ), 0),
        ).order_by('-paid_units', '-created_at')[:limit]
        return self._product_payload(candidates)

    def get_user_recommendations(self, user, limit=10):
        return {'products': self.get_product_recommendations(user, limit)}

    def get_similar_products(self, product, limit=10):
        candidates = (
            Product.objects.filter(
                sub_category_id=product.sub_category_id,
                status=Product.PUBLISHED,
                market__status=Market.PUBLISHED,
            )
            .exclude(pk=product.pk)
            .annotate(
                paid_units=Coalesce(Sum(
                    'orderitem__quantity',
                    filter=Q(orderitem__order__is_paid=True),
                ), 0),
            )
            .order_by('-paid_units', '-created_at')[:max(1, min(int(limit), 50))]
        )
        return self._product_payload(candidates)

    def demand_forecast(self, product, days=7):
        days = max(1, min(int(days), 30))
        history = list(
            AnalyticsDailyMetric.objects.filter(
                scope=AnalyticsDailyMetric.PRODUCT,
                product=product,
            ).order_by('-date').values('date', 'units_sold')[:30]
        )
        history.reverse()
        if not history:
            return {'product_id': str(product.id), 'forecast': [], 'basis': 'no_paid_sales_history'}
        values = [row['units_sold'] for row in history]
        recent = values[-7:]
        baseline = sum(recent) / len(recent)
        slope = (values[-1] - values[0]) / max(1, len(values) - 1)
        start_date = timezone.localdate() + timedelta(days=1)
        forecast = [
            {
                'date': (start_date + timedelta(days=index)).isoformat(),
                'predicted_units': max(0, round(baseline + slope * (index + 1), 2)),
            }
            for index in range(days)
        ]
        return {
            'product_id': str(product.id),
            'forecast': forecast,
            'basis': 'rolling_paid_units_with_linear_trend',
            'history_days': len(history),
        }


class DailyMetricBuilder:
    def rebuild(self, start_date, end_date):
        day = start_date
        rebuilt = 0
        while day <= end_date:
            self._rebuild_day(day)
            rebuilt += 1
            day += timedelta(days=1)
        return rebuilt

    @transaction.atomic
    def _rebuild_day(self, day):
        orders = Order.objects.filter(is_paid=True, created_at__date=day)
        items = OrderItem.objects.filter(order__in=orders)
        events = AnalyticsEvent.objects.filter(occurred_at__date=day)
        platform_views = events.filter(event_type=AnalyticsEvent.PRODUCT_VIEW)
        AnalyticsDailyMetric.objects.update_or_create(
            date=day,
            scope=AnalyticsDailyMetric.PLATFORM,
            market=None,
            product=None,
            defaults={
                'views': platform_views.count(),
                'unique_viewers': platform_views.filter(user__isnull=False).values('user_id').distinct().count(),
                'add_to_cart_count': events.filter(event_type=AnalyticsEvent.ADD_TO_CART).count(),
                'paid_orders': orders.count(),
                'units_sold': items.aggregate(value=Coalesce(Sum('quantity'), 0))['value'],
                'gross_revenue': _money(orders.aggregate(value=Sum('payable_amount'))['value']),
                'unique_buyers': orders.values('user_id').distinct().count(),
                'calculated_at': timezone.now(),
            },
        )
        market_ids = set(events.exclude(market=None).values_list('market_id', flat=True))
        market_ids.update(items.annotate(
            canonical_market_id=Coalesce('product__market_id', 'affiliate__market_id'),
        ).values_list('canonical_market_id', flat=True))
        for market_id in market_ids:
            market_items = items.filter(AnalyticsService._item_market_filter([market_id]))
            market_events = events.filter(market_id=market_id)
            views = market_events.filter(event_type=AnalyticsEvent.PRODUCT_VIEW)
            AnalyticsDailyMetric.objects.update_or_create(
                date=day, scope=AnalyticsDailyMetric.MARKET, market_id=market_id, product=None,
                defaults={
                    'views': views.count(),
                    'unique_viewers': views.filter(user__isnull=False).values('user_id').distinct().count(),
                    'add_to_cart_count': market_events.filter(event_type=AnalyticsEvent.ADD_TO_CART).count(),
                    'paid_orders': market_items.values('order_id').distinct().count(),
                    'units_sold': market_items.aggregate(value=Coalesce(Sum('quantity'), 0))['value'],
                    'gross_revenue': _money(market_items.aggregate(value=Sum(ExpressionWrapper(
                        F('unit_price') * F('quantity'),
                        output_field=DecimalField(max_digits=18, decimal_places=3),
                    )))['value']),
                    'unique_buyers': market_items.values('order__user_id').distinct().count(),
                    'calculated_at': timezone.now(),
                },
            )
        product_ids = set(events.exclude(product=None).values_list('product_id', flat=True))
        product_ids.update(items.annotate(
            canonical_product_id=Coalesce('product_id', 'affiliate__product_id'),
        ).values_list('canonical_product_id', flat=True))
        for product_id in product_ids:
            product_items = items.filter(Q(product_id=product_id) | Q(affiliate__product_id=product_id))
            product_events = events.filter(product_id=product_id)
            views = product_events.filter(event_type=AnalyticsEvent.PRODUCT_VIEW)
            market_id = Product.objects.only('market_id').get(pk=product_id).market_id
            AnalyticsDailyMetric.objects.update_or_create(
                date=day, scope=AnalyticsDailyMetric.PRODUCT, product_id=product_id,
                defaults={
                    'market_id': market_id,
                    'views': views.count(),
                    'unique_viewers': views.filter(user__isnull=False).values('user_id').distinct().count(),
                    'add_to_cart_count': product_events.filter(event_type=AnalyticsEvent.ADD_TO_CART).count(),
                    'paid_orders': product_items.values('order_id').distinct().count(),
                    'units_sold': product_items.aggregate(value=Coalesce(Sum('quantity'), 0))['value'],
                    'gross_revenue': _money(product_items.aggregate(value=Sum(ExpressionWrapper(
                        F('unit_price') * F('quantity'),
                        output_field=DecimalField(max_digits=18, decimal_places=3),
                    )))['value']),
                    'unique_buyers': product_items.values('order__user_id').distinct().count(),
                    'calculated_at': timezone.now(),
                },
            )


class ModelTrainer:
    """Optional-dependency model training with versioned JSON artifacts."""

    def __init__(self):
        self.root = Path(getattr(settings, 'ANALYTICS_MODEL_DIR', settings.BASE_DIR / 'ml_artifacts'))
        self.root.mkdir(parents=True, exist_ok=True)

    def train(self, model_types, activate_if_better=False):
        results = []
        for model_type in model_types:
            trainer = getattr(self, f'_train_{model_type}')
            payload, metrics, sample_count, started = trainer()
            results.append(self._store(model_type, payload, metrics, sample_count, started, activate_if_better))
        return results

    def _store(self, model_type, payload, metrics, sample_count, started, activate_if_better):
        ended = timezone.now()
        version = ended.strftime('%Y%m%d%H%M%S%f')
        path = self.root / f'{model_type}-{version}.json'
        encoded = json.dumps(payload, sort_keys=True, separators=(',', ':')).encode()
        path.write_bytes(encoded)
        checksum = hashlib.sha256(encoded).hexdigest()
        with transaction.atomic():
            artifact = MLModelArtifact.objects.create(
                model_type=model_type,
                version=version,
                training_started_at=started,
                training_ended_at=ended,
                sample_count=sample_count,
                validation_metrics=metrics,
                artifact_path=str(path),
                checksum=checksum,
            )
            if not activate_if_better or self._is_better(artifact):
                MLModelArtifact.objects.filter(model_type=model_type, is_active=True).update(is_active=False)
                artifact.is_active = True
                artifact.save(update_fields=['is_active'])
        return artifact

    @staticmethod
    def _is_better(candidate):
        current = MLModelArtifact.objects.filter(
            model_type=candidate.model_type,
            is_active=True,
        ).first()
        if current is None:
            return True
        metric_name = 'silhouette_score' if candidate.model_type == MLModelArtifact.RFM else 'mae'
        candidate_value = candidate.validation_metrics.get(metric_name)
        current_value = current.validation_metrics.get(metric_name)
        if candidate_value is None or current_value is None:
            return candidate.sample_count > current.sample_count
        return candidate_value > current_value if metric_name == 'silhouette_score' else candidate_value < current_value

    def _train_recommender(self):
        import numpy as np
        from sklearn.decomposition import NMF

        started = timezone.now()
        rows = list(
            OrderItem.objects.filter(order__is_paid=True)
            .annotate(product_ref=Coalesce('product_id', 'affiliate__product_id'))
            .values('order__user_id', 'product_ref')
            .annotate(weight=Sum('quantity'))
        )
        users = sorted({str(row['order__user_id']) for row in rows})
        products = sorted({str(row['product_ref']) for row in rows})
        if not users or not products:
            return {'scores': {}}, {'mae': 0.0}, 0, started
        matrix = np.zeros((len(users), len(products)))
        user_index = {value: index for index, value in enumerate(users)}
        product_index = {value: index for index, value in enumerate(products)}
        for row in rows:
            matrix[user_index[str(row['order__user_id'])], product_index[str(row['product_ref'])]] = row['weight']
        if len(users) < 2 or len(products) < 2:
            scores = {
                user: {
                    product: round(float(matrix[user_index[user], product_index[product]]), 6)
                    for product in products
                }
                for user in users
            }
            return {'scores': scores}, {'mae': 0.0}, len(rows), started
        components = max(1, min(8, len(users), len(products)))
        model = NMF(
            n_components=components,
            init='nndsvda',
            random_state=42,
            max_iter=1000,
            tol=1e-3,
        )
        reconstructed = model.fit_transform(matrix) @ model.components_
        mae = float(np.mean(np.abs(matrix - reconstructed)))
        scores = {
            user: {
                product: round(float(reconstructed[user_index[user], product_index[product]]), 6)
                for product in products
            }
            for user in users
        }
        return {'scores': scores}, {'mae': round(mae, 6)}, len(rows), started

    def _train_demand(self):
        import numpy as np
        from sklearn.linear_model import LinearRegression
        from sklearn.metrics import mean_absolute_error

        started = timezone.now()
        product_ids = AnalyticsDailyMetric.objects.filter(
            scope=AnalyticsDailyMetric.PRODUCT,
        ).values_list('product_id', flat=True).distinct()
        models = {}
        errors = []
        samples = 0
        for product_id in product_ids:
            values = list(AnalyticsDailyMetric.objects.filter(
                scope=AnalyticsDailyMetric.PRODUCT,
                product_id=product_id,
            ).order_by('date').values_list('units_sold', flat=True))
            if len(values) < 3:
                continue
            x = np.arange(len(values)).reshape(-1, 1)
            y = np.asarray(values, dtype=float)
            model = LinearRegression().fit(x, y)
            prediction = model.predict(x)
            errors.append(mean_absolute_error(y, prediction))
            samples += len(values)
            models[str(product_id)] = {
                'intercept': float(model.intercept_),
                'slope': float(model.coef_[0]),
                'history_length': len(values),
            }
        mae = float(sum(errors) / len(errors)) if errors else 0.0
        return {'products': models}, {'mae': round(mae, 6)}, samples, started

    def _train_rfm(self):
        import numpy as np
        from sklearn.cluster import KMeans
        from sklearn.metrics import silhouette_score
        from sklearn.preprocessing import StandardScaler

        started = timezone.now()
        now = timezone.now()
        rows = list(Order.objects.filter(is_paid=True).values('user_id').annotate(
            last_order=Coalesce(models_max('created_at'), now),
            frequency=Count('id'),
            monetary=Coalesce(Sum('payable_amount'), Decimal('0')),
        ))
        if len(rows) < 2:
            return {'segments': {}}, {'silhouette_score': 0.0}, len(rows), started
        features = np.asarray([
            [(now - row['last_order']).days, row['frequency'], float(row['monetary'])]
            for row in rows
        ], dtype=float)
        scaled = StandardScaler().fit_transform(features)
        clusters = min(4, len(rows))
        model = KMeans(n_clusters=clusters, random_state=42, n_init=10).fit(scaled)
        score = silhouette_score(scaled, model.labels_) if len(rows) > clusters and clusters > 1 else 0.0
        segments = {str(row['user_id']): int(label) for row, label in zip(rows, model.labels_)}
        return {'segments': segments}, {'silhouette_score': round(float(score), 6)}, len(rows), started


def models_max(field):
    """Keep the optional sklearn import path isolated from Django aggregation imports."""
    from django.db.models import Max
    return Max(field)


def acquire_training_lock(timeout=60 * 60 * 4):
    token = uuid.uuid4().hex
    acquired = cache.add('analytics:model-training-lock', token, timeout)
    return token if acquired else None


def release_training_lock(token):
    if cache.get('analytics:model-training-lock') == token:
        cache.delete('analytics:model-training-lock')
