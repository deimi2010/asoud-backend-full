"""Authoritative analytics data models.

Financial values never originate in these event rows. They are calculated from
paid orders and immutable order-item snapshots.
"""

import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone


class UserSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='analytics_sessions',
    )
    session_key = models.CharField(max_length=64, unique=True)
    started_at = models.DateTimeField(default=timezone.now)
    last_seen_at = models.DateTimeField(default=timezone.now)
    ended_at = models.DateTimeField(null=True, blank=True)
    duration = models.DurationField(null=True, blank=True, editable=False)
    is_active = models.BooleanField(default=True)
    device_type = models.CharField(max_length=32, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'analytics_user_session'
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['user', 'started_at']),
            models.Index(fields=['is_active', 'last_seen_at']),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(ended_at__isnull=True) | Q(ended_at__gte=models.F('started_at')),
                name='analytics_session_end_after_start',
            ),
        ]

    def save(self, *args, **kwargs):
        if self.ended_at:
            self.duration = self.ended_at - self.started_at
            self.last_seen_at = max(self.last_seen_at, self.ended_at)
            self.is_active = False
        else:
            self.duration = None
        super().save(*args, **kwargs)

    def end(self, at=None):
        self.ended_at = at or timezone.now()
        self.save(update_fields=[
            'ended_at', 'duration', 'last_seen_at', 'is_active', 'updated_at',
        ])


class AnalyticsEvent(models.Model):
    PRODUCT_VIEW = 'product_view'
    MARKET_VIEW = 'market_view'
    ADD_TO_CART = 'add_to_cart'
    BOOKMARK = 'bookmark'
    LOGIN = 'login'
    LOGOUT = 'logout'
    PAID_ORDER = 'paid_order'

    EVENT_TYPES = [
        (PRODUCT_VIEW, 'Product view'),
        (MARKET_VIEW, 'Market view'),
        (ADD_TO_CART, 'Add to cart'),
        (BOOKMARK, 'Bookmark'),
        (LOGIN, 'Login'),
        (LOGOUT, 'Logout'),
        (PAID_ORDER, 'Paid order'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='analytics_events',
    )
    session = models.ForeignKey(
        UserSession,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='events',
    )
    session_key = models.CharField(max_length=64, blank=True, default='', db_index=True)
    event_type = models.CharField(max_length=32, choices=EVENT_TYPES, db_index=True)
    product = models.ForeignKey(
        'product.Product',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='analytics_events',
    )
    market = models.ForeignKey(
        'market.Market',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='analytics_events',
    )
    order = models.ForeignKey(
        'cart.Order',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='analytics_events',
    )
    dedupe_key = models.CharField(max_length=128, unique=True, null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    occurred_at = models.DateTimeField(default=timezone.now, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'analytics_event'
        ordering = ['-occurred_at']
        indexes = [
            models.Index(fields=['user', 'occurred_at']),
            models.Index(fields=['event_type', 'occurred_at']),
            models.Index(fields=['product', 'event_type', 'occurred_at']),
            models.Index(fields=['market', 'event_type', 'occurred_at']),
        ]


class AnalyticsDailyMetric(models.Model):
    PLATFORM = 'platform'
    MARKET = 'market'
    PRODUCT = 'product'
    SCOPE_CHOICES = [
        (PLATFORM, 'Platform'),
        (MARKET, 'Market'),
        (PRODUCT, 'Product'),
    ]

    date = models.DateField()
    scope = models.CharField(max_length=16, choices=SCOPE_CHOICES)
    market = models.ForeignKey(
        'market.Market',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='daily_analytics',
    )
    product = models.ForeignKey(
        'product.Product',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='daily_analytics',
    )
    views = models.PositiveIntegerField(default=0)
    unique_viewers = models.PositiveIntegerField(default=0)
    add_to_cart_count = models.PositiveIntegerField(default=0)
    paid_orders = models.PositiveIntegerField(default=0)
    units_sold = models.PositiveIntegerField(default=0)
    gross_revenue = models.DecimalField(max_digits=18, decimal_places=3, default=0)
    unique_buyers = models.PositiveIntegerField(default=0)
    calculated_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'analytics_daily_metric'
        ordering = ['-date', 'scope']
        indexes = [
            models.Index(fields=['scope', 'date']),
            models.Index(fields=['market', 'date']),
            models.Index(fields=['product', 'date']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['date'],
                condition=Q(scope='platform', market__isnull=True, product__isnull=True),
                name='analytics_unique_platform_day',
            ),
            models.UniqueConstraint(
                fields=['date', 'market'],
                condition=Q(scope='market', market__isnull=False, product__isnull=True),
                name='analytics_unique_market_day',
            ),
            models.UniqueConstraint(
                fields=['date', 'product'],
                condition=Q(scope='product', product__isnull=False),
                name='analytics_unique_product_day',
            ),
            models.CheckConstraint(
                condition=(
                    Q(scope='platform', market__isnull=True, product__isnull=True)
                    | Q(scope='market', market__isnull=False, product__isnull=True)
                    | Q(scope='product', product__isnull=False)
                ),
                name='analytics_scope_dimensions_valid',
            ),
        ]


class MLModelArtifact(models.Model):
    RECOMMENDER = 'recommender'
    DEMAND = 'demand'
    RFM = 'rfm'
    MODEL_TYPES = [
        (RECOMMENDER, 'Recommender'),
        (DEMAND, 'Demand forecast'),
        (RFM, 'RFM segmentation'),
    ]

    model_type = models.CharField(max_length=24, choices=MODEL_TYPES, db_index=True)
    version = models.CharField(max_length=64)
    training_started_at = models.DateTimeField()
    training_ended_at = models.DateTimeField()
    sample_count = models.PositiveIntegerField()
    validation_metrics = models.JSONField(default=dict)
    artifact_path = models.CharField(max_length=500)
    checksum = models.CharField(max_length=64)
    is_active = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'analytics_ml_model_artifact'
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(fields=['model_type', 'version'], name='analytics_unique_model_version'),
            models.UniqueConstraint(
                fields=['model_type'],
                condition=Q(is_active=True),
                name='analytics_one_active_model_type',
            ),
        ]

