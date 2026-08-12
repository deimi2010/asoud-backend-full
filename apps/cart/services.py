from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP

from django.db import models, transaction
from django.utils import timezone

from apps.affiliate.models import AffiliateProduct
from apps.cart.models import Order
from apps.discount.models import Discount
from apps.product.models import Product


MONEY_QUANTUM = Decimal('0.001')


class CartIntegrityError(ValueError):
    def __init__(self, code: str, detail: str):
        self.code = code
        self.detail = detail
        super().__init__(detail)


def _target_market_id(item):
    if (item.product_id is None) == (item.affiliate_id is None):
        return None
    target = item.product or item.affiliate
    return target.market_id if target else None


def _lock_order(order):
    """Refresh the caller's instance while holding the authoritative order row lock."""
    locked_order = (
        Order.objects.select_for_update()
        .select_related('user')
        .get(id=order.id)
    )
    order.__dict__.update(locked_order.__dict__)
    return order


def _locked_items(order):
    items = list(
        order.items.select_for_update()
        .order_by('id')
    )
    affiliate_ids = sorted({item.affiliate_id for item in items if item.affiliate_id}, key=str)
    affiliate_refs = {
        row['id']: row
        for row in AffiliateProduct.objects.filter(id__in=affiliate_ids).values(
            'id', 'product_id'
        )
    }
    product_ids = sorted(
        {item.product_id for item in items if item.product_id}
        | {row['product_id'] for row in affiliate_refs.values()},
        key=str,
    )
    products = {
        product.id: product
        for product in Product.objects.select_for_update()
        .select_related('market')
        .filter(id__in=product_ids)
        .order_by('id')
    }
    affiliates = {
        affiliate.id: affiliate
        for affiliate in AffiliateProduct.objects.select_for_update()
        .select_related('market')
        .filter(id__in=affiliate_ids)
        .order_by('id')
    }
    for affiliate in affiliates.values():
        affiliate.product = products.get(affiliate.product_id)
    for item in items:
        if item.product_id:
            item.product = products.get(item.product_id)
        if item.affiliate_id:
            item.affiliate = affiliates.get(item.affiliate_id)
    return items


def _quantize(value):
    return Decimal(value).quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)


def validate_catalog_target(target):
    if target.status != target.PUBLISHED or target.market.status != target.market.PUBLISHED:
        raise CartIntegrityError('unavailable_item', f'{target.name} is not available.')
    if target.ship_cost_pay_type == target.CUSTOMER:
        raise CartIntegrityError(
            'shipping_contract_unavailable',
            'Customer-paid shipping is unavailable until checkout can select its price.',
        )
    if isinstance(target, AffiliateProduct):
        source = target.product
        if (
            source.status != source.PUBLISHED
            or not source.is_marketer
            or source.market.status != source.market.PUBLISHED
        ):
            raise CartIntegrityError(
                'unavailable_item',
                f'{target.name} is no longer available for affiliate marketing.',
            )
        if source.ship_cost_pay_type == source.CUSTOMER:
            raise CartIntegrityError(
                'shipping_contract_unavailable',
                'Customer-paid shipping is unavailable until checkout can select its price.',
            )


def _validate_items(items):
    if not items:
        raise CartIntegrityError('empty_order', 'Order is empty.')

    market_ids = {_target_market_id(item) for item in items}
    if None in market_ids:
        raise CartIntegrityError('invalid_item', 'Every order item must have exactly one target.')
    if len(market_ids) != 1:
        raise CartIntegrityError(
            'mixed_market_order',
            'All items in an order must belong to one market.',
        )

    product_quantities = defaultdict(int)
    affiliate_quantities = defaultdict(int)
    for item in items:
        if (item.product_id is None) == (item.affiliate_id is None):
            raise CartIntegrityError(
                'invalid_item',
                'Every order item must have exactly one target.',
            )
        if item.quantity < 1:
            raise CartIntegrityError('invalid_quantity', 'Item quantity must be positive.')
        target = item.product or item.affiliate
        validate_catalog_target(target)
        if item.product_id:
            product_quantities[item.product_id] += item.quantity
        else:
            affiliate_quantities[item.affiliate_id] += item.quantity

    for item in items:
        target = item.product or item.affiliate
        required = (
            product_quantities[item.product_id]
            if item.product_id
            else affiliate_quantities[item.affiliate_id]
        )
        if target.stock < required:
            raise CartIntegrityError(
                'insufficient_stock',
                f'Insufficient stock for {target.name}. Available: {target.stock}.',
            )
    return market_ids.pop()


def _discount_applies(discount, items, market_id):
    model = discount.content_type.model
    if model == 'market':
        return discount.object_id == market_id
    if model == 'product':
        return any(
            item.product_id == discount.object_id
            or (
                item.affiliate_id
                and item.affiliate.product_id == discount.object_id
            )
            for item in items
        )
    return False


def _validate_discount(discount, order, items, market_id, include_reservations=True):
    if discount.expiry and discount.expiry < timezone.now():
        raise CartIntegrityError('discount_expired', 'Discount code has expired.')
    used = discount.consumed + (discount.reserved if include_reservations else 0)
    if discount.limitation and used >= discount.limitation:
        raise CartIntegrityError('discount_limit_reached', 'Discount usage limit reached.')
    allowed_users = {str(value) for value in discount.users}
    if allowed_users and not {
        str(order.user_id),
        order.user.mobile_number,
    }.intersection(allowed_users):
        raise CartIntegrityError('discount_not_eligible', 'Discount is not available to this user.')
    if not _discount_applies(discount, items, market_id):
        raise CartIntegrityError('discount_not_applicable', 'Discount does not apply to this order.')
    previous_use = Order.objects.filter(
        user_id=order.user_id,
        discount_id=discount.id,
    ).exclude(id=order.id).filter(
        models.Q(is_paid=True)
        | models.Q(
            inventory_status__in=(
                Order.INVENTORY_RESERVED,
                Order.INVENTORY_CONFIRMED,
            )
        )
    ).exists()
    if previous_use:
        raise CartIntegrityError('discount_already_used', 'Discount was already used by this user.')


def _discountable_subtotal(discount, items):
    if discount.content_type.model == 'market':
        eligible = items
    else:
        eligible = [
            item
            for item in items
            if item.product_id == discount.object_id
            or (item.affiliate_id and item.affiliate.product_id == discount.object_id)
        ]
    return sum((item.total_price() for item in eligible), Decimal('0'))


@transaction.atomic
def clear_order_snapshot(order):
    order = _lock_order(order)
    order.discount = None
    order.discount_code_snapshot = ''
    order.discount_percentage_snapshot = 0
    order.subtotal_amount = None
    order.discount_amount = Decimal('0')
    order.payable_amount = None
    order.save(
        update_fields=[
            'discount',
            'discount_code_snapshot',
            'discount_percentage_snapshot',
            'subtotal_amount',
            'discount_amount',
            'payable_amount',
            'updated_at',
        ]
    )
    order.items.update(unit_price=None)


@transaction.atomic
def snapshot_order(order, discount_code=''):
    order = _lock_order(order)
    items = _locked_items(order)
    market_id = _validate_items(items)
    for item in items:
        target = item.product or item.affiliate
        item.unit_price = target.main_price if item.product_id else target.price
        item.save(update_fields=['unit_price', 'updated_at'])

    subtotal = _quantize(sum((item.total_price() for item in items), Decimal('0')))
    discount = None
    discount_amount = Decimal('0')
    if discount_code:
        try:
            discount = (
                Discount.objects.select_for_update()
                .select_related('content_type')
                .get(code__iexact=discount_code.strip())
            )
        except Discount.DoesNotExist as exc:
            raise CartIntegrityError('discount_not_found', 'Discount code is not valid.') from exc
        _validate_discount(discount, order, items, market_id, include_reservations=False)
        eligible_subtotal = _discountable_subtotal(discount, items)
        discount_amount = _quantize(
            eligible_subtotal * Decimal(discount.percentage) / Decimal('100')
        )

    order.discount = discount
    order.discount_code_snapshot = discount.code if discount else ''
    order.discount_percentage_snapshot = discount.percentage if discount else 0
    order.subtotal_amount = subtotal
    order.discount_amount = discount_amount
    order.payable_amount = _quantize(subtotal - discount_amount)
    if order.payable_amount <= 0:
        raise CartIntegrityError('invalid_total', 'Order total must be positive.')
    if (
        order.type == Order.ONLINE
        and order.payable_amount != order.payable_amount.to_integral_value()
    ):
        raise CartIntegrityError(
            'invalid_gateway_total',
            'Online order total must be a whole IRT value.',
        )
    order.save(
        update_fields=[
            'discount',
            'discount_code_snapshot',
            'discount_percentage_snapshot',
            'subtotal_amount',
            'discount_amount',
            'payable_amount',
            'updated_at',
        ]
    )
    return order


@transaction.atomic
def reserve_order_inventory(order):
    order = _lock_order(order)
    if order.inventory_status == Order.INVENTORY_RESERVED:
        return order
    if order.inventory_status != Order.INVENTORY_NONE:
        raise CartIntegrityError('inventory_state', 'Order inventory cannot be reserved.')
    if order.status not in (Order.PENDING, Order.VERIFIED):
        raise CartIntegrityError('invalid_status', 'Order is not reservable.')

    items = _locked_items(order)
    market_id = _validate_items(items)
    if order.payable_amount is None:
        snapshot_order(order, order.discount_code_snapshot)
        items = _locked_items(order)
    else:
        current_snapshot_subtotal = _quantize(
            sum((item.total_price() for item in items), Decimal('0'))
        )
        if current_snapshot_subtotal != order.subtotal_amount:
            raise CartIntegrityError(
                'order_changed',
                'Order items changed after checkout; create a new order.',
            )

    if order.discount_id:
        discount = (
            Discount.objects.select_for_update()
            .select_related('content_type')
            .get(id=order.discount_id)
        )
        _validate_discount(discount, order, items, market_id)
        discount.reserved += 1
        discount.save(update_fields=['reserved', 'updated_at'])

    for item in items:
        target = item.product or item.affiliate
        target.stock -= item.quantity
        target.save(update_fields=['stock', 'updated_at'])

    order.inventory_status = Order.INVENTORY_RESERVED
    order.save(update_fields=['inventory_status', 'updated_at'])
    return order


@transaction.atomic
def release_order_inventory(order, *, terminal=True):
    order = _lock_order(order)
    if order.inventory_status != Order.INVENTORY_RESERVED:
        return order
    items = _locked_items(order)
    for item in items:
        target = item.product or item.affiliate
        target.stock += item.quantity
        target.save(update_fields=['stock', 'updated_at'])
    if order.discount_id:
        discount = Discount.objects.select_for_update().get(id=order.discount_id)
        if discount.reserved < 1:
            raise CartIntegrityError('discount_state', 'Discount reservation is inconsistent.')
        discount.reserved -= 1
        discount.save(update_fields=['reserved', 'updated_at'])
    order.inventory_status = (
        Order.INVENTORY_RELEASED if terminal else Order.INVENTORY_NONE
    )
    order.save(update_fields=['inventory_status', 'updated_at'])
    return order


@transaction.atomic
def confirm_order_inventory(order):
    order = _lock_order(order)
    if order.inventory_status == Order.INVENTORY_CONFIRMED:
        return order
    if order.inventory_status != Order.INVENTORY_RESERVED:
        raise CartIntegrityError('inventory_state', 'Order has no inventory reservation.')
    if order.discount_id:
        discount = Discount.objects.select_for_update().get(id=order.discount_id)
        if discount.reserved < 1:
            raise CartIntegrityError('discount_state', 'Discount reservation is inconsistent.')
        discount.reserved -= 1
        discount.consumed += 1
        discount.save(update_fields=['reserved', 'consumed', 'updated_at'])
    order.inventory_status = Order.INVENTORY_CONFIRMED
    order.save(update_fields=['inventory_status', 'updated_at'])
    return order
