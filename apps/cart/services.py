from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP

from django.db import models, transaction
from django.utils import timezone

from apps.affiliate.models import AffiliateProduct
from apps.cart.models import Order
from apps.discount.models import Discount
from apps.market.models import MarketShippingMethod
from apps.product.models import Product, ProductDiscount


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


def _item_requires_store_shipping(item):
    target = item.product or item.affiliate
    return (
        target.type == Product.GOOD
        and target.sell_type != Product.PERSON
        and target.ship_cost_pay_type in (
            Product.STORE_SHIPPING,
            Product.CUSTOMER,  # legacy value
        )
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
    if not discount.is_active:
        raise CartIntegrityError('discount_inactive', 'Discount code is inactive.')
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


def _code_discount_applies_to_item(discount, item, market_id):
    if discount is None:
        return False
    if discount.content_type.model == 'market':
        return discount.object_id == market_id
    product_id = item.product_id or (
        item.affiliate.product_id if item.affiliate_id else None
    )
    return (
        discount.content_type.model == 'product'
        and discount.object_id == product_id
    )


def _automatic_discounts(items, order):
    product_ids = {
        item.product_id or item.affiliate.product_id
        for item in items
    }
    rows = list(
        ProductDiscount.objects.select_for_update()
        .filter(product_id__in=product_ids, is_active=True)
        .order_by('product_id', '-percentage', '-created_at')
    )
    now = timezone.now()
    result = {}
    for discount in rows:
        if discount.product_id in result:
            continue
        if discount.expiry and discount.expiry <= now:
            continue
        if (
            discount.discount_type == ProductDiscount.GROUP
            and (
                discount.limitation <= discount.consumed + discount.reserved
                or discount.users.filter(id=order.user_id).exists()
            )
        ):
            continue
        result[discount.product_id] = discount
    return result


def _validate_automatic_discount(discount, order):
    if not discount.is_active or (discount.expiry and discount.expiry <= timezone.now()):
        raise CartIntegrityError('product_discount_inactive', 'Product discount is unavailable.')
    if discount.discount_type == ProductDiscount.GROUP:
        if discount.users.filter(id=order.user_id).exists():
            raise CartIntegrityError(
                'product_discount_already_used',
                'Group product discount was already used by this customer.',
            )
        already_reserved = discount.order_items.filter(
            order__user_id=order.user_id,
            order__inventory_status=Order.INVENTORY_RESERVED,
        ).exclude(order_id=order.id).exists()
        if already_reserved:
            raise CartIntegrityError(
                'product_discount_already_reserved',
                'Group product discount is already reserved for this customer.',
            )
        if discount.limitation <= discount.consumed + discount.reserved:
            raise CartIntegrityError(
                'product_discount_limit_reached',
                'Group product discount capacity has been reached.',
            )


@transaction.atomic
def clear_order_snapshot(order):
    order = _lock_order(order)
    order.discount = None
    order.discount_code_snapshot = ''
    order.discount_percentage_snapshot = 0
    order.subtotal_amount = None
    order.discount_amount = Decimal('0')
    order.shipping_method = None
    order.shipping_method_name_snapshot = ''
    order.shipping_amount = Decimal('0')
    order.payable_amount = None
    order.save(
        update_fields=[
            'discount',
            'discount_code_snapshot',
            'discount_percentage_snapshot',
            'subtotal_amount',
            'discount_amount',
            'shipping_method',
            'shipping_method_name_snapshot',
            'shipping_amount',
            'payable_amount',
            'updated_at',
        ]
    )
    order.items.update(
        unit_price=None,
        product_discount=None,
        product_discount_percentage_snapshot=0,
    )


@transaction.atomic
def snapshot_order(order, discount_code='', shipping_method_id=None):
    order = _lock_order(order)
    items = _locked_items(order)
    market_id = _validate_items(items)
    discount = None
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

    shipping_required = any(_item_requires_store_shipping(item) for item in items)
    shipping_method = None
    if shipping_required:
        if not shipping_method_id:
            raise CartIntegrityError(
                'shipping_method_required',
                'Select one shipping method for this order.',
            )
        try:
            shipping_method = MarketShippingMethod.objects.select_for_update().get(
                id=shipping_method_id,
                market_id=market_id,
                is_active=True,
            )
        except MarketShippingMethod.DoesNotExist as exc:
            raise CartIntegrityError(
                'shipping_method_invalid',
                'Selected shipping method is unavailable for this store.',
            ) from exc
    elif shipping_method_id:
        raise CartIntegrityError(
            'shipping_not_required',
            'This order does not require a paid shipping method.',
        )

    automatic = _automatic_discounts(items, order)
    subtotal = Decimal('0')
    payable = Decimal('0')
    code_was_used = False
    for item in items:
        target = item.product or item.affiliate
        base_price = target.main_price if item.product_id else target.price
        product_id = item.product_id or item.affiliate.product_id
        automatic_discount = automatic.get(product_id)
        automatic_percentage = automatic_discount.percentage if automatic_discount else 0
        code_percentage = (
            discount.percentage
            if _code_discount_applies_to_item(discount, item, market_id)
            else 0
        )

        # Discounts never stack. On a tie, prefer the code so a group slot is not consumed.
        automatic_wins = automatic_percentage > code_percentage
        applied_percentage = automatic_percentage if automatic_wins else code_percentage
        code_was_used = code_was_used or (code_percentage > 0 and not automatic_wins)
        item.unit_price = _quantize(
            Decimal(base_price) * (Decimal('100') - Decimal(applied_percentage))
            / Decimal('100')
        )
        item.product_discount = automatic_discount if automatic_wins else None
        item.product_discount_percentage_snapshot = (
            automatic_percentage if automatic_wins else 0
        )
        item.save(update_fields=[
            'unit_price',
            'product_discount',
            'product_discount_percentage_snapshot',
            'updated_at',
        ])
        subtotal += Decimal(base_price) * item.quantity
        payable += item.unit_price * item.quantity

    subtotal = _quantize(subtotal)
    payable = _quantize(payable)
    if discount is not None and not code_was_used:
        discount = None
    discount_amount = _quantize(subtotal - payable)
    shipping_amount = _quantize(shipping_method.price if shipping_method else 0)

    order.discount = discount
    order.discount_code_snapshot = discount.code if discount else ''
    order.discount_percentage_snapshot = discount.percentage if discount else 0
    order.subtotal_amount = subtotal
    order.discount_amount = discount_amount
    order.shipping_method = shipping_method
    order.shipping_method_name_snapshot = shipping_method.name if shipping_method else ''
    order.shipping_amount = shipping_amount
    order.payable_amount = _quantize(payable + shipping_amount)
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
            'shipping_method',
            'shipping_method_name_snapshot',
            'shipping_amount',
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
        snapshot_order(
            order,
            order.discount_code_snapshot,
            order.shipping_method_id,
        )
        items = _locked_items(order)
    else:
        current_snapshot_subtotal = _quantize(
            sum((item.total_price() for item in items), Decimal('0'))
        )
        if _quantize(current_snapshot_subtotal + order.shipping_amount) != order.payable_amount:
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

    product_discount_ids = {item.product_discount_id for item in items if item.product_discount_id}
    for product_discount in ProductDiscount.objects.select_for_update().filter(
        id__in=product_discount_ids,
    ).order_by('id'):
        _validate_automatic_discount(product_discount, order)
        if product_discount.discount_type == ProductDiscount.GROUP:
            product_discount.reserved += 1
            product_discount.save(update_fields=['reserved', 'updated_at'])

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
    product_discount_ids = {item.product_discount_id for item in items if item.product_discount_id}
    for product_discount in ProductDiscount.objects.select_for_update().filter(
        id__in=product_discount_ids,
    ).order_by('id'):
        if product_discount.discount_type == ProductDiscount.GROUP:
            if product_discount.reserved < 1:
                raise CartIntegrityError(
                    'product_discount_state',
                    'Product discount reservation is inconsistent.',
                )
            product_discount.reserved -= 1
            product_discount.save(update_fields=['reserved', 'updated_at'])
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
    items = _locked_items(order)
    product_discount_ids = {item.product_discount_id for item in items if item.product_discount_id}
    for product_discount in ProductDiscount.objects.select_for_update().filter(
        id__in=product_discount_ids,
    ).order_by('id'):
        if product_discount.discount_type == ProductDiscount.GROUP:
            if product_discount.reserved < 1:
                raise CartIntegrityError(
                    'product_discount_state',
                    'Product discount reservation is inconsistent.',
                )
            product_discount.reserved -= 1
            product_discount.consumed += 1
            product_discount.save(update_fields=['reserved', 'consumed', 'updated_at'])
            product_discount.users.add(order.user)
    order.inventory_status = Order.INVENTORY_CONFIRMED
    order.save(update_fields=['inventory_status', 'updated_at'])
    return order
