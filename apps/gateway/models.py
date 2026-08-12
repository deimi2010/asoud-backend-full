from django.utils.translation import gettext_lazy as _
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey

from apps.base.models import models, BaseModel

# Create your models here.


class Gateway(BaseModel):
    PENDING = 'pending'
    SUCCESS = 'success'
    FAILED = 'failed'
    UNKNOWN = 'unknown'

    STATUS_CHOICES = (
        (PENDING, _('Pending')),
        (SUCCESS, _('Success')),
        (FAILED, _('Failed')),
        (UNKNOWN, _('Unknown')),
    )

    # Generic relation to either Cart or MarketSubscription
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        verbose_name=_('Content Type'),
    )
    object_id = models.PositiveIntegerField(
        verbose_name=_('Object ID'),
    )
    related_object = GenericForeignKey(
        'content_type',
        'object_id',
    )
    invoice_number = models.CharField(
        max_length=10,
        verbose_name=_('Invoice number'),
    )
    amount = models.DecimalField(
        max_digits=14,
        decimal_places=3,
        verbose_name=_('Amount'),
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=PENDING,
        verbose_name=_('Status'),
    )
    reference_number = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name=_('Reference number'),
    )
    track_id = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name=_('Reference number'),
    )

    class Meta:
        db_table = 'gateway'
        verbose_name = _('Gateway')
        verbose_name_plural = _('Gateways')

    def __str__(self):
        return self.invoice_number
