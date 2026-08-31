import logging
from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.db.models import F
from django.utils import timezone

from apps.notification.models import NotificationTemplate
from apps.notification.services import NotificationService
from apps.reserve.models import Reservation
from apps.users.models import User
from apps.wallet.models import Transaction, Wallet

logger = logging.getLogger(__name__)


def reservation_market(reservation):
    if reservation.service_id:
        return reservation.service.market
    if reservation.reserve_id:
        return reservation.reserve.service.market
    return None


def appointment_link(reservation):
    return f'https://asoud.ir/appointments/{reservation.tracking_code}'


def _sms_copy(reservation, event):
    market = reservation_market(reservation)
    market_name = market.name if market else 'فروشگاه'
    service_name = reservation.service_name_snapshot or (
        reservation.service.name if reservation.service_id else 'خدمت'
    )
    when = timezone.localtime(reservation.scheduled_start).strftime('%Y/%m/%d - %H:%M')
    messages = {
        'requested': f'درخواست نوبت شما در {market_name} برای {service_name} در {when} ثبت شد و منتظر تأیید است.',
        'confirmed': f'نوبت شما در {market_name} برای {service_name} در {when} قطعی شد.',
        'rescheduled': f'زمان نوبت شما در {market_name} به {when} تغییر کرد.',
        'cancelled': f'نوبت شما در {market_name} برای {service_name} لغو شد.',
        'reminder_24h': f'یادآوری: نوبت شما در {market_name} در {when} است.',
        'reminder_2h': f'یادآوری: حدود دو ساعت تا نوبت شما در {market_name} باقی مانده است.',
    }
    message = messages.get(event)
    if not message:
        return None
    refund = ''
    if event == 'cancelled' and reservation.refund_amount > 0:
        refund = f' مبلغ {reservation.refund_amount:g} به کیف پول شما برگشت داده شد.'
    return f'{message}{refund}\nکد پیگیری: {reservation.tracking_code}\n{appointment_link(reservation)}'


def send_appointment_sms(reservation_id, event):
    try:
        reservation = Reservation.objects.select_related(
            'user', 'service__market', 'reserve__service__market',
        ).get(id=reservation_id)
        body = _sms_copy(reservation, event)
        if not body:
            return False
        return NotificationService().send_notification(
            user=reservation.user,
            notification_type=NotificationTemplate.APPOINTMENT_UPDATE,
            title='اطلاع‌رسانی نوبت آسود',
            body=body,
            channel=NotificationTemplate.SMS,
            data={
                'reservation_id': str(reservation.id),
                'tracking_code': reservation.tracking_code,
                'link': appointment_link(reservation),
                'event': event,
            },
            priority='high',
            force=True,
        )
    except Exception:
        logger.exception('Appointment SMS dispatch failed for %s', reservation_id)
        return False


def notify_after_commit(reservation, event):
    reservation_id = reservation.id
    transaction.on_commit(lambda: send_appointment_sms(reservation_id, event))


def refund_paid_reservation(reservation, reason):
    """Idempotently refund a cancelled paid appointment to the user's wallet."""
    if not reservation.is_paid or reservation.amount_due <= 0 or reservation.refunded_at:
        return Decimal('0')
    User.objects.select_for_update().get(id=reservation.user_id)
    wallet, _ = Wallet.objects.get_or_create(user_id=reservation.user_id)
    wallet = Wallet.objects.select_for_update().get(id=wallet.id)
    amount = reservation.amount_due
    wallet.balance = F('balance') + amount
    wallet.save(update_fields=('balance', 'updated_at'))
    Transaction.objects.create(
        user_id=reservation.user_id,
        from_wallet=wallet,
        to_wallet=wallet,
        action=f'appointment_refund:{reservation.id}',
        amount=amount,
    )
    reservation.refund_amount = amount
    reservation.refunded_at = timezone.now()
    reservation.cancellation_reason = reason
    reservation.save(update_fields=(
        'refund_amount', 'refunded_at', 'cancellation_reason', 'updated_at',
    ))
    return amount


def process_appointment_reminders(now=None, batch_size=100):
    now = now or timezone.now()
    sent = 0
    with transaction.atomic():
        reminders_24h = list(
            Reservation.objects.select_for_update(skip_locked=True).filter(
                status=Reservation.CONFIRMED,
                scheduled_start__gt=now + timedelta(hours=2),
                scheduled_start__lte=now + timedelta(hours=24),
                reminder_24h_sent_at__isnull=True,
            ).order_by('scheduled_start')[:batch_size]
        )
        for reservation in reminders_24h:
            reservation.reminder_24h_sent_at = now
            reservation.save(update_fields=('reminder_24h_sent_at', 'updated_at'))
            notify_after_commit(reservation, 'reminder_24h')
            sent += 1
    with transaction.atomic():
        reminders_2h = list(
            Reservation.objects.select_for_update(skip_locked=True).filter(
                status=Reservation.CONFIRMED,
                scheduled_start__gt=now,
                scheduled_start__lte=now + timedelta(hours=2),
                reminder_2h_sent_at__isnull=True,
            ).order_by('scheduled_start')[:batch_size]
        )
        for reservation in reminders_2h:
            reservation.reminder_2h_sent_at = now
            reservation.save(update_fields=('reminder_2h_sent_at', 'updated_at'))
            notify_after_commit(reservation, 'reminder_2h')
            sent += 1
    return sent
