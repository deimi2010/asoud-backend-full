"""Server-authoritative analytics event hooks."""

from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.cart.models import Order
from apps.market.models import MarketBookmark

from .models import AnalyticsEvent
from .services import AnalyticsRecorder


@receiver(post_save, sender=Order)
def record_paid_order(sender, instance, **kwargs):
    if not instance.is_paid:
        return
    order_id = instance.pk

    def record():
        order = Order.objects.select_related('user').get(pk=order_id)
        AnalyticsRecorder.record(
            AnalyticsEvent.PAID_ORDER,
            user=order.user,
            order=order,
            dedupe_key=f'paid-order:{order.pk}',
        )

    transaction.on_commit(record)


@receiver(post_save, sender=MarketBookmark)
def record_market_bookmark(sender, instance, **kwargs):
    if not instance.is_active:
        return
    bookmark_id = instance.pk

    def record():
        bookmark = MarketBookmark.objects.select_related('user', 'market').get(pk=bookmark_id)
        AnalyticsRecorder.record(
            AnalyticsEvent.BOOKMARK,
            user=bookmark.user,
            market=bookmark.market,
            metadata={'bookmarked': True},
            dedupe_key=f'market-bookmark:{bookmark.pk}:active',
        )

    transaction.on_commit(record)
