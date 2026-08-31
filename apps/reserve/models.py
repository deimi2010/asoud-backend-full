import uuid
from decimal import Decimal

from apps.base.models import models, BaseModel
from apps.core.money import MONEY_DECIMAL_PLACES, MONEY_MAX_DIGITS
from apps.users.models import User
from apps.market.models import Market
from apps.product.models import Product
from django.core.validators import MaxValueValidator, MinValueValidator
from django.utils.translation import gettext_lazy as _


def reservation_tracking_code():
    return f"AS-{uuid.uuid4().hex[:10].upper()}"

class Service(BaseModel):
    FREE = 'free'
    FIXED = 'fixed'
    DEPOSIT_PERCENT = 'deposit_percent'
    FULL = 'full'
    PAYMENT_MODE_CHOICES = (
        (FREE, _('Free reservation')),
        (FIXED, _('Fixed reservation fee')),
        (DEPOSIT_PERCENT, _('Deposit percentage')),
        (FULL, _('Full service price')),
    )

    market = models.ForeignKey(
        Market,
        related_name='services',
        on_delete=models.CASCADE,
        verbose_name=_('Market')
    )
    
    name = models.CharField(
        max_length=32,
        verbose_name=_('name')
    )

    product = models.OneToOneField(
        Product,
        related_name='appointment_service',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name=_('Service product'),
    )
    duration_minutes = models.PositiveSmallIntegerField(
        default=30,
        validators=[MinValueValidator(5), MaxValueValidator(720)],
        verbose_name=_('Appointment duration in minutes'),
    )
    buffer_minutes = models.PositiveSmallIntegerField(
        default=0,
        validators=[MaxValueValidator(180)],
        verbose_name=_('Buffer between appointments in minutes'),
    )
    capacity = models.PositiveSmallIntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(100)],
        verbose_name=_('Capacity per slot'),
    )
    payment_mode = models.CharField(
        max_length=24,
        choices=PAYMENT_MODE_CHOICES,
        default=FREE,
    )
    fixed_fee = models.DecimalField(
        max_digits=MONEY_MAX_DIGITS,
        decimal_places=MONEY_DECIMAL_PLACES,
        default=Decimal('0'),
        validators=[MinValueValidator(Decimal('0'))],
    )
    deposit_percentage = models.PositiveSmallIntegerField(
        default=0,
        validators=[MaxValueValidator(100)],
    )
    requires_owner_confirmation = models.BooleanField(default=False)
    max_advance_days = models.PositiveSmallIntegerField(default=90)
    cancellation_hours = models.PositiveSmallIntegerField(default=24)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "service"
        verbose_name = _('Service')
        verbose_name_plural = _('Services')

    def __str__(self):
        return self.name

class Specialist(BaseModel):
    user = models.CharField(
        max_length=64,
        verbose_name=_('User')
    )

    market = models.ForeignKey(
        Market,
        related_name='appointment_specialists',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    account = models.ForeignKey(
        User,
        related_name='specialist_profiles',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    is_active = models.BooleanField(default=True)

    services = models.ManyToManyField(
        Service,
        blank=True,
        verbose_name=_('Services')
    )
    
    field = models.CharField(
        max_length=32,
        null=True,
        blank=True,
        verbose_name=_('Field')
    )

    class Meta:
        db_table = "specialist"
        verbose_name = _('Specialist')
        verbose_name_plural = _('Specialists')
        
    def __str__(self):
        return str(self.id)[:4]

class ReserveTime(BaseModel):
    SATURDAY    = '1'
    SUNDAY      = '2'
    MONDAY      = '3'
    TUESDAY     = '4'
    WEDNESDAY   = '5'
    THURSDAY    = '6'
    FRIDAY      = '7'

    DAY_CHOICES = [
        (SATURDAY, _('Saturday')),
        (SUNDAY, _('Sunday')),
        (MONDAY, _('Monday')),
        (TUESDAY, _('Tuesday')),
        (WEDNESDAY, _('Wednesday')),
        (THURSDAY, _('Thursday')),
        (FRIDAY, _('Friday')),
    ]

    service = models.ForeignKey(
        Service,
        related_name='reserve_times',
        on_delete=models.CASCADE,
        verbose_name=_('Service')
    )

    day = models.CharField(
        max_length=1,
        choices=DAY_CHOICES,
        verbose_name=_('Day'),
    )

    start = models.TimeField(
        verbose_name=_('StartTime')
    )

    end = models.TimeField(
        null=True,
        blank=True,
        verbose_name=_('EndTime')
    )

    class Meta:
        db_table = "reserve_time"
        verbose_name = _('ReserveTime')
        verbose_name_plural = _('ReserveTimes')
        
    def __str__(self):
        return str(self.id)[:4]
    
class DayOff(BaseModel):
    market = models.ForeignKey(
        Market,
        related_name='day_offs',
        on_delete=models.CASCADE,
        verbose_name=_('Market')
    )
    date = models.DateField(
        verbose_name=_('Date')
    )

    def __str__(self):
        return f"{self.market.name} - {self.date}"

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=('market', 'date'), name='uniq_market_day_off'),
        ]


class SpecialistTimeOff(BaseModel):
    specialist = models.ForeignKey(
        Specialist,
        related_name='time_offs',
        on_delete=models.CASCADE,
    )
    date = models.DateField()
    start = models.TimeField(null=True, blank=True)
    end = models.TimeField(null=True, blank=True)
    reason = models.CharField(max_length=160, blank=True, default='')

    class Meta:
        ordering = ('date', 'start')
        constraints = [
            models.UniqueConstraint(
                fields=('specialist', 'date', 'start', 'end'),
                name='uniq_specialist_time_off',
            ),
        ]

class Reservation(BaseModel):
    HELD = 'held'
    PENDING_CONFIRMATION = 'pending_confirmation'
    CONFIRMED = 'confirmed'
    COMPLETED = 'completed'
    CANCELLED = 'cancelled'
    NO_SHOW = 'no_show'
    EXPIRED = 'expired'
    STATUS_CHOICES = (
        (HELD, _('Held for payment')),
        (PENDING_CONFIRMATION, _('Pending owner confirmation')),
        (CONFIRMED, _('Confirmed')),
        (COMPLETED, _('Completed')),
        (CANCELLED, _('Cancelled')),
        (NO_SHOW, _('No show')),
        (EXPIRED, _('Expired')),
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name=_('User')
    )

    reserve = models.ForeignKey(
        ReserveTime,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name=_('ReservedService')
    )

    service = models.ForeignKey(
        Service,
        related_name='reservations',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )

    specialist = models.ForeignKey(
        Specialist,
        on_delete=models.CASCADE,
        verbose_name=_('Specialist')
    )

    is_paid = models.BooleanField(
        default=False,
        verbose_name=_('Is Paid')
    )
    scheduled_start = models.DateTimeField(null=True, blank=True)
    scheduled_end = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=24, choices=STATUS_CHOICES, default=HELD)
    hold_expires_at = models.DateTimeField(null=True, blank=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancellation_reason = models.CharField(max_length=240, blank=True, default='')
    tracking_code = models.CharField(
        max_length=16,
        unique=True,
        default=reservation_tracking_code,
        editable=False,
    )
    service_name_snapshot = models.CharField(max_length=100, blank=True, default='')
    price_snapshot = models.DecimalField(
        max_digits=MONEY_MAX_DIGITS,
        decimal_places=MONEY_DECIMAL_PLACES,
        default=Decimal('0'),
    )
    payment_mode_snapshot = models.CharField(max_length=24, blank=True, default='free')
    amount_due = models.DecimalField(
        max_digits=MONEY_MAX_DIGITS,
        decimal_places=MONEY_DECIMAL_PLACES,
        default=Decimal('0'),
    )
    refund_amount = models.DecimalField(
        max_digits=MONEY_MAX_DIGITS,
        decimal_places=MONEY_DECIMAL_PLACES,
        default=Decimal('0'),
    )
    refunded_at = models.DateTimeField(null=True, blank=True)
    reminder_24h_sent_at = models.DateTimeField(null=True, blank=True)
    reminder_2h_sent_at = models.DateTimeField(null=True, blank=True)
    class Meta:
        db_table = "reservation"
        verbose_name = _('Reservation')
        verbose_name_plural = _('Reservations')
        indexes = [
            # Performance optimization indexes
            models.Index(fields=['user', 'is_paid'], name='idx_reservation_user_paid'),
            models.Index(fields=['specialist', 'created_at'], name='idx_res_spec_created'),
            models.Index(fields=['reserve', 'created_at'], name='idx_reservation_reserve_date'),
            models.Index(fields=['is_paid', 'created_at'], name='idx_reservation_paid_date'),
            models.Index(fields=['specialist', 'scheduled_start'], name='idx_res_spec_start'),
            models.Index(fields=['status', 'hold_expires_at'], name='idx_res_status_expiry'),
        ]
        
    def __str__(self):
        return str(self.id)[:4]
    
