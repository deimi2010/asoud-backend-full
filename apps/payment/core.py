import logging
import os
from datetime import timedelta
from decimal import Decimal, InvalidOperation
from types import SimpleNamespace

import requests
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.utils import timezone

from apps.cart.models import Order
from apps.cart.services import (
    CartIntegrityError,
    confirm_order_inventory,
    release_order_inventory,
    reserve_order_inventory,
)
from apps.payment.models import Payment, Zarinpal
from apps.market.models import Market
from apps.users.models import User
from apps.wallet.core import WalletCore
from apps.wallet.models import Wallet


logger = logging.getLogger(__name__)


def validate_payment_amount(amount, max_amount=None):
    """Validate payment amount is positive, finite, and within bounds.
    
    Args:
        amount: Decimal amount to validate
        max_amount: Optional maximum allowed amount (default: 1 billion Rial)
    
    Returns:
        Tuple (is_valid, error_message)
    """
    if max_amount is None:
        max_amount = Decimal('1000000000')  # 1 billion Rial max
    
    try:
        amount = Decimal(str(amount))
    except (InvalidOperation, TypeError, ValueError):
        return False, "Amount must be a valid number"
    
    if not amount.is_finite():
        return False, "Amount must be a finite number"
    
    if amount <= 0:
        return False, "Amount must be positive"
    
    if amount > max_amount:
        return False, f"Amount exceeds maximum allowed: {max_amount}"
    
    # Normalize to remove trailing zeros, then check decimal places
    normalized = amount.normalize()
    if normalized.as_tuple().exponent < -2:
        return False, "Amount cannot have more than 2 decimal places"
    
    return True, None
    """Reconcile stale gateway sessions without guessing their financial state."""
    if cutoff is None:
        ttl_seconds = getattr(settings, 'PAYMENT_SESSION_TTL_SECONDS', 30 * 60)
        cutoff = timezone.now() - timedelta(seconds=ttl_seconds)

    session_ids = list(
        Payment.objects.filter(
            status=Payment.PENDING,
            created_at__lt=cutoff,
        ).order_by('created_at').values_list('id', flat=True)[:limit]
    )
    result = {'checked': 0, 'completed': 0, 'released': 0, 'ambiguous': 0}
    for payment_id in session_ids:
        payment = Payment.objects.select_related('zarinpal_data').get(id=payment_id)
        try:
            gateway = payment.zarinpal_data
        except Zarinpal.DoesNotExist:
            result['ambiguous'] += 1
            continue
        if not gateway.authority:
            # A provider request may have succeeded even if its response was lost.
            # Without an authority there is no safe automated release decision.
            result['ambiguous'] += 1
            continue

        result['checked'] += 1
        PaymentCore().verify(
            SimpleNamespace(GET={'Authority': gateway.authority, 'Status': 'OK'})
        )
        payment.refresh_from_db()
        if payment.status == Payment.COMPLETE:
            result['completed'] += 1
        elif payment.status in (Payment.FAILED, Payment.CANCELED):
            result['released'] += 1
        else:
            result['ambiguous'] += 1
    return result


class PaymentCore:
    request_timeout = 10
    integrity_version = 1

    def pay(self, user, data):
        target = data.get('resolved_target')
        requested_amount = data.get('resolved_amount')
        if target is None or requested_amount is None or not isinstance(target, (Wallet, Order)):
            return False, 'Invalid payment target'

        merchant_id = getattr(settings, 'ZARINPAL_MERCHANT_ID', '') or os.environ.get(
            'ZARINPAL_MERCHANT_ID'
        )
        if not merchant_id:
            return False, 'Payment gateway is not configured'

        target_content_type = ContentType.objects.get_for_model(target)
        gateway_content_type = ContentType.objects.get_for_model(Zarinpal)

        callback_url = os.environ.get('PAYMENT_CALLBACK_URL') or getattr(
            settings,
            'PAYMENT_CALLBACK_URL',
            'https://asoud.ir/api/v1/user/payments/verify/',
        )
        gateway_subdomain = getattr(settings, 'ZARINPAL_URL', 'api')
        url = f'https://{gateway_subdomain}.zarinpal.com/pg/v4/payment/request.json'

        with transaction.atomic():
            # All financial writes use User as the first per-user mutex.
            User.objects.select_for_update().get(id=user.id)
            if isinstance(target, Order):
                try:
                    target = (
                        Order.objects.select_for_update()
                        .prefetch_related('items__product', 'items__affiliate')
                        .get(
                            id=target.id,
                            user=user,
                            status__in=(Order.PENDING, Order.VERIFIED, Order.PROCESSING),
                            type=Order.ONLINE,
                            is_paid=False,
                        )
                    )
                except Order.DoesNotExist:
                    return False, 'Payable order not found'

                existing_payment = (
                    Payment.objects.filter(
                        user=user,
                        target_content_type=target_content_type,
                        target_id=target.id,
                        status=Payment.PENDING,
                    )
                    .first()
                )
                if existing_payment is not None:
                    existing_gateway = Zarinpal.objects.filter(
                        payment=existing_payment,
                    ).first()
                    gateway_metadata = (
                        existing_gateway.verification_data
                        if existing_gateway is not None
                        else None
                    )
                    if (
                        existing_gateway
                        and existing_gateway.authority
                        and isinstance(gateway_metadata, dict)
                        and gateway_metadata.get('integrity_version') == self.integrity_version
                    ):
                        return True, existing_gateway
                    return False, 'Existing payment session requires reconciliation'

                if target.status not in (Order.PENDING, Order.VERIFIED) or not target.items.exists():
                    return False, 'Order is not payable'
                amount = Decimal(str(target.total_price()))
                
                # Validate amount before proceeding
                is_valid, validation_error = validate_payment_amount(amount)
                if not is_valid:
                    return False, validation_error
                
                if amount != Decimal(str(requested_amount)):
                    return False, 'Order total changed; refresh before paying'

                try:
                    reserve_order_inventory(target)
                except CartIntegrityError as exc:
                    return False, exc.detail

                target.status = Order.PROCESSING
                target.save(update_fields=['status', 'updated_at'])
            else:
                try:
                    target = Wallet.objects.select_for_update().get(id=target.id, user=user)
                except Wallet.DoesNotExist:
                    return False, 'Wallet not found'
                amount = Decimal(str(requested_amount))

            payment = Payment.objects.create(
                user=user,
                amount=amount,
                target_content_type=target_content_type,
                target_id=target.id,
                gateway_content_type=gateway_content_type,
                status=Payment.PENDING,
            )
            zarinpal = Zarinpal.objects.create(
                payment=payment,
                authority='',
                verification_data={'integrity_version': self.integrity_version},
            )
            payment.gateway_id = zarinpal.id
            payment.save(update_fields=['gateway_id', 'updated_at'])

        # The target freeze is committed before the provider call so cart
        # mutations cannot continue seeing the order as pending while the
        # network is slow.
        payload = {
            'merchant_id': merchant_id,
            'amount': int(amount),
            'currency': 'IRT',
            'description': 'Asoud payment',
            'callback_url': callback_url,
            'meta_data': {'payment': str(payment.id)},
        }
        try:
            response = requests.post(url=url, json=payload, timeout=self.request_timeout)
            response.raise_for_status()
            response_data = response.json()
            authority = response_data['data']['authority']
            if not authority:
                raise ValueError('Gateway returned an empty authority')
        except (requests.RequestException, ValueError, KeyError, TypeError) as exc:
            logger.warning('Payment request failed for payment %s: %s', payment.id, exc)
            with transaction.atomic():
                failed_payment = (
                    Payment.objects.select_for_update()
                    .get(id=payment.id)
                )
                if failed_payment.status == Payment.PENDING:
                    failed_payment.status = Payment.FAILED
                    failed_payment.save(update_fields=['status', 'updated_at'])
                    self._release_order(failed_payment)
            return False, 'Unable to create payment session'

        with transaction.atomic():
            zarinpal = Zarinpal.objects.select_for_update().get(id=zarinpal.id)
            locked_payment = Payment.objects.select_for_update().get(id=payment.id)
            if locked_payment.status != Payment.PENDING:
                return False, 'Payment session is no longer pending'
            if zarinpal.authority and zarinpal.authority != authority:
                return False, 'Payment authority requires reconciliation'
            zarinpal.authority = authority
            zarinpal.save(update_fields=['authority', 'updated_at'])
        return True, zarinpal

    def verify(self, request):
        authority = request.GET.get('Authority')
        gateway_status = request.GET.get('Status')
        if not authority or not gateway_status:
            return False, 'No verification data was provided'

        try:
            with transaction.atomic():
                zarinpal = (
                    Zarinpal.objects.select_for_update()
                    .get(authority=authority)
                )
                payment = Payment.objects.select_for_update().get(id=zarinpal.payment_id)

                if zarinpal.transaction_id and payment.status == Payment.COMPLETE:
                    return True, 'Payment already processed'
                if payment.status != Payment.PENDING:
                    return False, 'Payment is no longer pending'
                gateway_metadata = zarinpal.verification_data
                if (
                    not isinstance(gateway_metadata, dict)
                    or gateway_metadata.get('integrity_version') != self.integrity_version
                ):
                    return False, 'Legacy payment session requires reconciliation'
                if gateway_status != 'OK':
                    payment.status = Payment.CANCELED
                    payment.save(update_fields=['status', 'updated_at'])
                    self._release_order(payment)
                    return False, 'Payment was canceled at the gateway'

                merchant_id = getattr(
                    settings, 'ZARINPAL_MERCHANT_ID', ''
                ) or os.environ.get('ZARINPAL_MERCHANT_ID')
                if not merchant_id:
                    return False, 'Payment gateway is not configured'

                payload = {
                    'merchant_id': merchant_id,
                    'amount': int(payment.amount),
                    'authority': authority,
                }
                gateway_subdomain = getattr(settings, 'ZARINPAL_URL', 'api')
                url = f'https://{gateway_subdomain}.zarinpal.com/pg/v4/payment/verify.json'
                try:
                    response = requests.post(
                        url=url,
                        json=payload,
                        timeout=self.request_timeout,
                    )
                    response.raise_for_status()
                    response_data = response.json()
                except (requests.RequestException, ValueError, TypeError) as exc:
                    logger.warning(
                        'Payment verification request failed for authority %s: %s',
                        authority,
                        exc,
                    )
                    return False, 'Unable to verify payment with gateway'

                try:
                    gateway_data = response_data['data']
                    code = int(gateway_data['code'])
                except (KeyError, TypeError, ValueError):
                    return False, 'Gateway response requires reconciliation'

                # 101 means the gateway has already verified the authority. If
                # our local transaction was interrupted, processing it here is
                # the safe recovery path.
                if code not in (100, 101):
                    payment.status = Payment.FAILED
                    payment.save(update_fields=['status', 'updated_at'])
                    self._release_order(payment)
                    return False, 'Payment verification failed'

                reference_id = gateway_data.get('ref_id')
                if reference_id is None:
                    return False, 'Gateway reference ID requires reconciliation'

                verified_amount = gateway_data.get('amount')
                if verified_amount is not None:
                    try:
                        if Decimal(str(verified_amount)) != Decimal(str(payment.amount)):
                            return False, 'Payment amount mismatch requires reconciliation'
                    except InvalidOperation:
                        return False, 'Gateway amount requires reconciliation'

                PostPaymentCore(payment.user).payment_process(payment)

                zarinpal.transaction_id = str(reference_id)
                zarinpal.verification_data = response_data
                zarinpal.save(update_fields=['transaction_id', 'verification_data', 'updated_at'])
                payment.status = Payment.COMPLETE
                payment.save(update_fields=['status', 'updated_at'])
        except Zarinpal.DoesNotExist:
            return False, 'No payment found'
        except (Order.DoesNotExist, Wallet.DoesNotExist, Market.DoesNotExist, ValueError) as exc:
            logger.warning('Post-payment processing failed for authority %s: %s', authority, exc)
            return False, str(exc)

        return True, 'Payment successful'

    @staticmethod
    def _release_order(payment):
        if (
            payment.target_content_type_id
            and payment.target_content_type.model_class() is Order
        ):
            has_other_pending_payment = Payment.objects.filter(
                target_content_type=payment.target_content_type,
                target_id=payment.target_id,
                status=Payment.PENDING,
            ).exclude(id=payment.id).exists()
            if has_other_pending_payment:
                return
            try:
                order = Order.objects.select_for_update().get(
                    id=payment.target_id,
                    user=payment.user,
                    status=Order.PROCESSING,
                    is_paid=False,
                )
            except Order.DoesNotExist:
                return
            release_order_inventory(order)
            order.status = Order.FAILED
            order.save(update_fields=['status', 'updated_at'])


class PostPaymentCore:
    def __init__(self, user):
        self.user = user

    def payment_process(self, payment: Payment):
        target_model = payment.target_content_type.model_class()
        if target_model is Wallet:
            success, result = WalletCore.increase_balance(
                self.user,
                payment.target_id,
                payment.amount,
            )
            if not success:
                raise ValueError(result)
            return

        if target_model is Order:
            self.complete_order(payment.target_id, payment.amount)
            return

        if target_model is Market:
            market = Market.objects.select_for_update().get(
                id=payment.target_id,
                user=self.user,
            )
            if market.status == Market.DRAFT:
                market.status = Market.QUEUE
                market.save(update_fields=['status', 'updated_at'])
            return

        raise ValueError('Unsupported payment target')

    def wallet_process(self, target: str, pk: str, amount=None, wallet_id: str = None):
        if target == 'wallet':
            return WalletCore.transaction(self.user, wallet_id, pk, amount)

        if target != 'order':
            return False, 'Unsupported wallet payment target'

        try:
            with transaction.atomic():
                # Match cart and online-payment lock order: User -> Order.
                User.objects.select_for_update().get(id=self.user.id)
                order = (
                    Order.objects.select_for_update()
                    .prefetch_related('items__product', 'items__affiliate')
                    .get(
                        id=pk,
                        user=self.user,
                        status__in=(Order.PENDING, Order.VERIFIED),
                        type=Order.ONLINE,
                        is_paid=False,
                    )
                )
                expected_amount = Decimal(str(order.total_price()))
                requested_amount = Decimal(str(amount))
                
                # Validate both amounts
                is_valid, error = validate_payment_amount(expected_amount)
                if not is_valid:
                    return False, f"Order amount invalid: {error}"
                
                is_valid, error = validate_payment_amount(requested_amount)
                if not is_valid:
                    return False, f"Requested amount invalid: {error}"
                
                if expected_amount <= 0 or requested_amount != expected_amount:
                    return False, 'Amount does not match the current order total'

                try:
                    reserve_order_inventory(order)
                except CartIntegrityError as exc:
                    return False, exc.detail

                success, result = WalletCore.decrease_balance(
                    self.user,
                    wallet_id,
                    expected_amount,
                )
                if not success:
                    release_order_inventory(order, terminal=False)
                    return False, result

                confirm_order_inventory(order)
                order.status = Order.COMPLETED
                order.is_paid = True
                order.save(update_fields=['status', 'is_paid', 'updated_at'])
        except Order.DoesNotExist:
            return False, 'Payable order not found'
        except (InvalidOperation, TypeError, ValueError) as exc:
            return False, str(exc)

        return True, 'Payment successful'

    def complete_order(self, pk: str, paid_amount):
        paid_amount = Decimal(str(paid_amount))
        if not paid_amount.is_finite() or paid_amount <= 0:
            raise ValueError('Invalid paid amount')

        order = (
            Order.objects.select_for_update()
            .get(
                id=pk,
                user=self.user,
                status=Order.PROCESSING,
                is_paid=False,
            )
        )

        confirm_order_inventory(order)
        order.status = Order.COMPLETED
        order.is_paid = True
        order.save(update_fields=['status', 'is_paid', 'updated_at'])
