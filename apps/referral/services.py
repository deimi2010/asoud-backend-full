from django.db.models import F
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal, ROUND_HALF_UP

from apps.referral.models import (
    MarketInviteLink, Referral, ReferralCommission, ReferralLevel, StoreAccess,
)


def get_valid_invite(token, *, for_update=False):
    query = MarketInviteLink.objects.select_related('market', 'created_by')
    if for_update:
        query = query.select_for_update()
    try:
        invite = query.get(token=token, is_active=True)
    except (MarketInviteLink.DoesNotExist, TypeError, ValueError, ValidationError):
        return None
    if invite.expires_at and invite.expires_at <= timezone.now():
        return None
    if invite.market.status != invite.market.PUBLISHED:
        return None
    return invite


def accept_store_invite(*, user, invite, allow_referral_attribution=False):
    """Grant store access; attribution is permitted only during first signup."""
    access, _ = StoreAccess.objects.update_or_create(
        user=user,
        market=invite.market,
        defaults={
            'invite_link': invite,
            'verified_at': timezone.now(),
            'is_active': True,
        },
    )
    referral = None
    if allow_referral_attribution and invite.created_by_id != user.id:
        referral, created = Referral.objects.get_or_create(
            referred_user=user,
            defaults={
                'referred_by': invite.created_by,
                'market': invite.market,
                'invite_link': invite,
            },
        )
        if created:
            MarketInviteLink.objects.filter(pk=invite.pk).update(
                use_count=F('use_count') + 1
            )
    return access, referral


def accrue_store_publication_commissions(*, market, payment):
    """Create an idempotent seven-level ledger from an actual completed payment."""
    if payment.amount is None:
        return []
    levels = {item.level: item for item in ReferralLevel.objects.filter(is_active=True)}
    source_user = market.user
    current_user = source_user
    commissions = []
    for level_number in range(1, 8):
        referral = Referral.objects.select_related('referred_by').filter(
            referred_user=current_user,
        ).first()
        if referral is None or referral.referred_by is None:
            break
        beneficiary = referral.referred_by
        level_config = levels.get(level_number)
        if level_config is not None:
            amount = (
                Decimal(payment.amount) * level_config.percentage / Decimal('100')
            ).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            commission, _ = ReferralCommission.objects.get_or_create(
                payment=payment,
                beneficiary=beneficiary,
                level=level_number,
                defaults={
                    'market': market,
                    'source_user': source_user,
                    'base_amount': payment.amount,
                    'percentage': level_config.percentage,
                    'amount': amount,
                },
            )
            commissions.append(commission)
        current_user = beneficiary
    return commissions
