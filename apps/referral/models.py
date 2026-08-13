from apps.base.models import models, BaseModel
import uuid

from apps.market.models import Market
from apps.users.models import User
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.validators import MaxValueValidator, MinValueValidator
from decimal import Decimal
# Create your models here.

class Referral(BaseModel):
    referred_by = models.ForeignKey(
        User,
        related_name='referrals_made',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Referred By")
    )
    referred_user = models.OneToOneField(
        User,
        related_name='referral',
        on_delete=models.CASCADE,
        verbose_name=_("Referred User")
    )
    market = models.ForeignKey(
        Market,
        related_name='referrals',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name=_("Market"),
    )
    invite_link = models.ForeignKey(
        'MarketInviteLink',
        related_name='referrals',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    def __str__(self):
        return f"{self.referred_user} referred by {self.referred_by}"


class MarketInviteLink(BaseModel):
    """A revocable storefront invitation with stable attribution."""

    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    market = models.ForeignKey(
        Market,
        related_name='invite_links',
        on_delete=models.CASCADE,
    )
    created_by = models.ForeignKey(
        User,
        related_name='market_invite_links',
        on_delete=models.CASCADE,
    )
    is_active = models.BooleanField(default=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    use_count = models.PositiveBigIntegerField(default=0)

    class Meta:
        indexes = [
            models.Index(fields=('market', 'is_active'), name='invite_market_active_idx'),
        ]


class StoreAccess(BaseModel):
    """A customer's OTP-verified permission to view one storefront."""

    user = models.ForeignKey(
        User,
        related_name='store_accesses',
        on_delete=models.CASCADE,
    )
    market = models.ForeignKey(
        Market,
        related_name='customer_accesses',
        on_delete=models.CASCADE,
    )
    invite_link = models.ForeignKey(
        MarketInviteLink,
        related_name='store_accesses',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    verified_at = models.DateTimeField(default=timezone.now)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=('user', 'market'),
                name='unique_user_store_access',
            ),
        ]
        indexes = [
            models.Index(
                fields=('user', 'is_active'),
                name='store_access_user_active_idx',
            ),
        ]


class SignupInviteIntent(BaseModel):
    """Durable first-registration attribution, consumed after OTP verification."""

    user = models.OneToOneField(
        User,
        related_name='signup_invite_intent',
        on_delete=models.CASCADE,
    )
    invite_link = models.ForeignKey(
        MarketInviteLink,
        related_name='signup_intents',
        on_delete=models.CASCADE,
    )
    consumed_at = models.DateTimeField(null=True, blank=True)


class ReferralLevel(BaseModel):
    """Admin-configurable percentage for one of the seven uplines."""

    level = models.PositiveSmallIntegerField(
        unique=True,
        validators=[MinValueValidator(1), MaxValueValidator(7)],
    )
    percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('100'))],
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ('level',)


class ReferralCommission(BaseModel):
    ACCRUED = 'accrued'
    PAID = 'paid'
    CANCELED = 'canceled'
    STATUS_CHOICES = ((ACCRUED, 'Accrued'), (PAID, 'Paid'), (CANCELED, 'Canceled'))

    payment = models.ForeignKey(
        'payment.Payment',
        related_name='referral_commissions',
        on_delete=models.PROTECT,
    )
    market = models.ForeignKey(
        Market,
        related_name='referral_commissions',
        on_delete=models.PROTECT,
    )
    source_user = models.ForeignKey(
        User,
        related_name='generated_referral_commissions',
        on_delete=models.PROTECT,
    )
    beneficiary = models.ForeignKey(
        User,
        related_name='referral_commissions',
        on_delete=models.PROTECT,
    )
    level = models.PositiveSmallIntegerField()
    base_amount = models.DecimalField(max_digits=18, decimal_places=2)
    percentage = models.DecimalField(max_digits=5, decimal_places=2)
    amount = models.DecimalField(max_digits=18, decimal_places=2)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=ACCRUED)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=('payment', 'beneficiary', 'level'),
                name='unique_payment_referral_commission',
            ),
        ]
        indexes = [
            models.Index(fields=('beneficiary', 'status'), name='commission_beneficiary_idx'),
        ]
