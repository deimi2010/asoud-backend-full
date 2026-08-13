from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from apps.market.models import (
    Market, MarketContact, MarketLocation, MarketRevision, MarketTheme,
)
from apps.market.serializers.owner_serializers import (
    MarketContactUpdaterSerializer,
    MarketLocationUpdateSerializer,
    MarketThemeCreateSerializer,
    MarketUpdateSerializer,
)
from apps.payment.models import Payment


@transaction.atomic
def review_market_revision(*, revision, reviewer, action, reason=''):
    revision = MarketRevision.objects.select_for_update().select_related('market').get(
        pk=revision.pk,
        status=MarketRevision.PENDING,
    )
    market = Market.objects.select_for_update().get(pk=revision.market_id)
    if action == 'approve':
        payload = dict(revision.payload)
        location_payload = payload.pop('location', None)
        contact_payload = payload.pop('contact', None)
        theme_payload = payload.pop('theme', None)
        if payload:
            serializer = MarketUpdateSerializer(market, data=payload)
            serializer.is_valid(raise_exception=True)
            serializer.save()
        if location_payload is not None:
            location = MarketLocation.objects.select_for_update().get(market=market)
            serializer = MarketLocationUpdateSerializer(location, data=location_payload)
            serializer.is_valid(raise_exception=True)
            serializer.save()
        if contact_payload is not None:
            contact = MarketContact.objects.select_for_update().get(market=market)
            serializer = MarketContactUpdaterSerializer(contact, data=contact_payload, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
        if theme_payload is not None:
            theme = MarketTheme.objects.select_for_update().filter(market=market).first()
            serializer = MarketThemeCreateSerializer(theme, data=theme_payload)
            serializer.is_valid(raise_exception=True)
            serializer.save(market=market)
        revision.status = MarketRevision.APPROVED
    else:
        revision.status = MarketRevision.REJECTED
    revision.reviewed_by = reviewer
    revision.reviewed_at = timezone.now()
    revision.rejection_reason = reason
    revision.save(update_fields=[
        'status', 'reviewed_by', 'reviewed_at', 'rejection_reason', 'updated_at'
    ])
    return revision


@transaction.atomic
def review_market_publication(*, market, reviewer, action, payment=None):
    del reviewer  # reserved for the publication audit model introduced with the real baseline
    market = Market.objects.select_for_update().get(pk=market.pk)
    if action == 'reject':
        if market.status == Market.PUBLISHED:
            raise serializers.ValidationError({'action': 'A published store cannot be rejected.'})
        market.status = Market.NEEDS_EDITING
        market.save(update_fields=['status', 'updated_at'])
        return market, []

    if payment is None:
        raise serializers.ValidationError({'payment_id': 'Required for publication.'})
    payment = Payment.objects.select_for_update().get(pk=payment.pk)
    if payment.status != Payment.COMPLETE or payment.user_id != market.user_id:
        raise serializers.ValidationError({'payment_id': 'Completed store payment required.'})
    if payment.target_id != market.id or not payment.target_content_type:
        raise serializers.ValidationError({'payment_id': 'Payment is not for this store.'})
    if payment.target_content_type.model_class() is not Market:
        raise serializers.ValidationError({'payment_id': 'Payment is not for this store.'})

    market.status = Market.PUBLISHED
    market.is_paid = True
    market.save(update_fields=['status', 'is_paid', 'updated_at'])
    from apps.referral.services import accrue_store_publication_commissions

    commissions = accrue_store_publication_commissions(market=market, payment=payment)
    return market, commissions
