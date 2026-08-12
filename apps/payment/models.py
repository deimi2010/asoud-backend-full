from apps.base.models import models, BaseModel
from apps.users.models import User
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator
from decimal import Decimal

from apps.core.money import MONEY_DECIMAL_PLACES, MONEY_MAX_DIGITS


# Create your models here.
class Payment(BaseModel):
    PENDING = 'pending'
    COMPLETE = 'completed'
    FAILED = 'failed'
    CANCELED = 'canceled'

    STATUS_CHOICES = [
        (PENDING, _('Pending')),
        (COMPLETE, _('Completed')),
        (FAILED, _('Failed')),
        (CANCELED, _('Canceled'))
    ]

    user = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL,
        # it actually should not be null unless the user deletes account
        null=True,
        related_name="payments",
        verbose_name=_('User')
    )
    amount = models.DecimalField(
        max_digits=MONEY_MAX_DIGITS,
        decimal_places=MONEY_DECIMAL_PLACES,
        null=True, 
        blank=True,
        validators=[MinValueValidator(Decimal("1"))],
        verbose_name=_('Amount')
    )

    target_content_type = models.ForeignKey(
        ContentType,
        on_delete=models.SET_NULL,
        related_name="target_payments",
        null=True,
        blank=True,
        verbose_name=_('Target Content Type')
    )
    target_id = models.UUIDField(
        null=True, 
        blank=True,
        verbose_name=_('Target ID')
    )
    target = GenericForeignKey(
        'target_content_type', 
        'target_id'
    )

    gateway_content_type = models.ForeignKey(
        ContentType,
        on_delete=models.SET_NULL,
        related_name="gateway_payments",
        null=True,
        blank=True,
        verbose_name=_('Gateway Content Type')
    )
    gateway_id = models.UUIDField(
        null=True, 
        blank=True
    )
    gateway = GenericForeignKey(
        'gateway_content_type', 
        'gateway_id'
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=PENDING,
        verbose_name=_('Status')
    )

    class Meta:
        ordering = ['-created_at']
        indexes = [
            # Performance optimization indexes
            models.Index(fields=['user', 'status'], name='idx_payment_user_status'),
            models.Index(fields=['status', 'created_at'], name='idx_payment_status_created'),
            models.Index(fields=['user', 'created_at'], name='idx_payment_user_created'),
            models.Index(fields=['target_content_type', 'target_id'], name='idx_payment_target'),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount__isnull=True) | models.Q(amount__gt=0),
                name='payment_amount_positive_or_null',
            ),
        ]

    def __str__(self):
        return str(self.id)[:4]
    
class Zarinpal(BaseModel):
    payment = models.OneToOneField(
        Payment,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='zarinpal_data',
        verbose_name=_('Payment')
    )
    authority = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        verbose_name=_('Authority')
    )
    transaction_id = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        verbose_name=_('Transaction ID')
    )
    verification_data = models.JSONField(
        null=True, 
        blank=True,
        verbose_name=_('Verification Data')
    )
    
    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['authority'],
                condition=models.Q(authority__isnull=False) & ~models.Q(authority=''),
                name='payment_zarinpal_authority_unique',
            ),
            models.UniqueConstraint(
                fields=['transaction_id'],
                condition=(
                    models.Q(transaction_id__isnull=False)
                    & ~models.Q(transaction_id='')
                ),
                name='payment_zarinpal_transaction_unique',
            ),
        ]

