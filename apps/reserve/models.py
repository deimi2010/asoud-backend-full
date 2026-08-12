from apps.base.models import models, BaseModel
from apps.users.models import User
from apps.market.models import Market
from django.utils.translation import gettext_lazy as _

# Create your models here.

class Service(BaseModel):
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

class Reservation(BaseModel):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name=_('User')
    )

    reserve = models.ForeignKey(
        ReserveTime,
        on_delete=models.CASCADE,
        verbose_name=_('ReservedService')
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
        ]
        
    def __str__(self):
        return str(self.id)[:4]
    
