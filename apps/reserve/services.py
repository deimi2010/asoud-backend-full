from datetime import datetime, timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.market.models import MarketSchedule
from apps.reserve.models import DayOff, Reservation, Service, Specialist, SpecialistTimeOff


ACTIVE_RESERVATION_STATUSES = (
    Reservation.HELD,
    Reservation.PENDING_CONFIRMATION,
    Reservation.CONFIRMED,
)
HOLD_MINUTES = 10


def market_weekday(value):
    """Convert Python Monday=0 numbering to the app's Saturday=0 contract."""
    return (value.weekday() + 2) % 7


def expire_stale_holds(now=None):
    now = now or timezone.now()
    return Reservation.objects.filter(
        status=Reservation.HELD,
        hold_expires_at__lte=now,
        is_paid=False,
    ).update(status=Reservation.EXPIRED)


def appointment_amount(service):
    price = Decimal(str(service.product.main_price if service.product_id else 0))
    if service.payment_mode == Service.FIXED:
        return service.fixed_fee
    if service.payment_mode == Service.DEPOSIT_PERCENT:
        return price * Decimal(service.deposit_percentage) / Decimal('100')
    if service.payment_mode == Service.FULL:
        return price
    return Decimal('0')


def _is_time_off(specialist, day, start_time, end_time):
    for item in SpecialistTimeOff.objects.filter(specialist=specialist, date=day):
        if item.start is None or item.end is None:
            return True
        if item.start < end_time and item.end > start_time:
            return True
    return False


def available_slots(*, service, specialist, day, now=None, exclude_reservation_id=None):
    now = now or timezone.now()
    expire_stale_holds(now)
    if (
        not service.is_active
        or not specialist.is_active
        or specialist.market_id != service.market_id
        or not specialist.services.filter(id=service.id).exists()
        or DayOff.objects.filter(market=service.market, date=day).exists()
    ):
        return []
    local_now = timezone.localtime(now)
    if day < local_now.date() or day > local_now.date() + timedelta(days=service.max_advance_days):
        return []
    duration = timedelta(minutes=service.duration_minutes)
    step = timedelta(minutes=service.duration_minutes + service.buffer_minutes)
    schedules = MarketSchedule.objects.filter(
        market=service.market,
        day_of_week=market_weekday(day),
    ).order_by('start_time')
    slots = []
    for schedule in schedules:
        cursor = timezone.make_aware(datetime.combine(day, schedule.start_time))
        interval_end = timezone.make_aware(datetime.combine(day, schedule.end_time))
        while cursor + duration <= interval_end:
            slot_end = cursor + duration
            if cursor > now and not _is_time_off(
                specialist,
                day,
                timezone.localtime(cursor).time(),
                timezone.localtime(slot_end).time(),
            ):
                occupied = Reservation.objects.filter(
                    specialist=specialist,
                    scheduled_start__lt=slot_end,
                    scheduled_end__gt=cursor,
                    status__in=ACTIVE_RESERVATION_STATUSES,
                )
                if exclude_reservation_id:
                    occupied = occupied.exclude(id=exclude_reservation_id)
                used = occupied.count()
                slots.append({
                    'start': cursor,
                    'end': slot_end,
                    'capacity': service.capacity,
                    'remaining': max(service.capacity - used, 0),
                    'available': used < service.capacity,
                })
            cursor += step
    return slots


@transaction.atomic
def hold_reservation(*, user, service, specialist, scheduled_start):
    now = timezone.now()
    specialist = Specialist.objects.select_for_update().get(
        id=specialist.id,
        is_active=True,
        market=service.market,
    )
    # Lock only the service row. PostgreSQL rejects FOR UPDATE when a
    # select_related() outer join includes nullable relations such as product.
    service = Service.objects.select_for_update().get(
        id=service.id,
        is_active=True,
    )
    local_start = timezone.localtime(scheduled_start)
    slot = next(
        (
            item for item in available_slots(
                service=service,
                specialist=specialist,
                day=local_start.date(),
                now=now,
            )
            if item['start'] == scheduled_start and item['available']
        ),
        None,
    )
    if slot is None:
        raise ValueError('Selected appointment is no longer available.')
    amount = appointment_amount(service)
    requires_payment = amount > 0
    status = Reservation.HELD if requires_payment else (
        Reservation.PENDING_CONFIRMATION
        if service.requires_owner_confirmation
        else Reservation.CONFIRMED
    )
    return Reservation.objects.create(
        user=user,
        service=service,
        specialist=specialist,
        scheduled_start=slot['start'],
        scheduled_end=slot['end'],
        status=status,
        hold_expires_at=now + timedelta(minutes=HOLD_MINUTES) if requires_payment else None,
        confirmed_at=now if status == Reservation.CONFIRMED else None,
        service_name_snapshot=service.product.name if service.product_id else service.name,
        price_snapshot=service.product.main_price if service.product_id else Decimal('0'),
        payment_mode_snapshot=service.payment_mode,
        amount_due=amount,
        is_paid=not requires_payment,
    )
