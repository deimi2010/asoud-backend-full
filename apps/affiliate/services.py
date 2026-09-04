from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.affiliate.models import AffiliateCommission


MONEY_QUANTUM = Decimal('0.001')


def _money(value):
    return Decimal(value).quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)


@transaction.atomic
def accrue_order_commissions(order):
    """Create immutable, idempotent affiliate sale ledger rows after payment."""
    for item in order.items.select_related(
        'affiliate__market__user', 'affiliate__product__market__user',
    ).filter(affiliate__isnull=False):
        if item.seller_settlement_unit_snapshot is None:
            continue
        gross = _money(item.affiliate_gross_unit_snapshot * item.quantity)
        fee = _money(
            (item.affiliate_platform_fee_unit_snapshot or Decimal('0'))
            * item.quantity
        )
        AffiliateCommission.objects.get_or_create(
            order_item=item,
            defaults={
                'order': order,
                'affiliate_product': item.affiliate,
                'seller': item.affiliate.product.market.user,
                'marketer': item.affiliate.market.user,
                'quantity': item.quantity,
                'customer_total': _money(item.unit_price * item.quantity),
                'seller_total': _money(
                    item.seller_settlement_unit_snapshot * item.quantity
                ),
                'gross_commission': gross,
                'platform_fee': fee,
                'marketer_total': _money(gross - fee),
                'status': AffiliateCommission.HELD,
            },
        )


@transaction.atomic
def schedule_order_commissions(order):
    hold_days = max(0, int(getattr(settings, 'AFFILIATE_RETURN_HOLD_DAYS', 7)))
    available_at = timezone.now() + timedelta(days=hold_days)
    order.affiliate_commissions.select_for_update().filter(
        status=AffiliateCommission.HELD,
    ).update(
        available_at=available_at,
        seller_available_at=available_at,
        updated_at=timezone.now(),
    )


@transaction.atomic
def release_due_commissions(marketer=None):
    rows = AffiliateCommission.objects.select_for_update().filter(
        status=AffiliateCommission.HELD,
        available_at__isnull=False,
        available_at__lte=timezone.now(),
    )
    if marketer is not None:
        rows = rows.filter(marketer=marketer)
    updated = rows.update(status=AffiliateCommission.AVAILABLE, updated_at=timezone.now())
    seller_rows = AffiliateCommission.objects.select_for_update().filter(
        seller_status=AffiliateCommission.HELD,
        seller_available_at__isnull=False,
        seller_available_at__lte=timezone.now(),
    )
    if marketer is not None:
        seller_rows = seller_rows.filter(seller=marketer)
    seller_rows.update(seller_status=AffiliateCommission.AVAILABLE, updated_at=timezone.now())
    return updated


@transaction.atomic
def reverse_order_commissions(order, reason):
    return order.affiliate_commissions.select_for_update().exclude(
        status=AffiliateCommission.PAID,
    ).update(
        status=AffiliateCommission.REVERSED,
        seller_status=AffiliateCommission.REVERSED,
        reversal_reason=reason[:255],
        updated_at=timezone.now(),
    )
