import math
from decimal import Decimal

from django.db import transaction
from django.db.models import F
from django.utils import timezone

from apps.sms.models import SmsCampaign, SmsRecipient, SmsTariff
from apps.sms.sms_core import SMSCoreHandler
from apps.users.models import UserDocument, UserProfile
from apps.wallet.models import Transaction, Wallet


def sms_eligibility(user):
    profile = UserProfile.objects.filter(user=user).first()
    required = {item[0] for item in UserDocument.DOCUMENT_TYPE_CHOICES}
    approved_docs = set(UserDocument.objects.filter(
        user=user, status=UserDocument.APPROVED,
    ).values_list('document_type', flat=True))
    missing_documents = sorted(required - approved_docs)
    eligible = bool(
        profile and profile.status == UserProfile.APPROVED
        and profile.phone_ownership_status == UserProfile.PHONE_OWNER_MATCHED
        and not missing_documents
    )
    return {
        'eligible': eligible,
        'profile_status': profile.status if profile else 'missing',
        'phone_ownership_status': profile.phone_ownership_status if profile else 'unchecked',
        'missing_documents': missing_documents,
        'mobile_number': user.mobile_number,
        'mobile_number_read_only': True,
    }


def segment_count(text, tariff):
    if not text:
        return 0
    is_persian = any('\u0600' <= char <= '\u06ff' for char in text)
    first = tariff.persian_first_segment_chars if is_persian else tariff.latin_first_segment_chars
    subsequent = tariff.persian_next_segment_chars if is_persian else tariff.latin_next_segment_chars
    return 1 if len(text) <= first else 1 + math.ceil((len(text) - first) / subsequent)


def active_tariff():
    return SmsTariff.objects.filter(is_active=True, effective_from__lte=timezone.now()).first()


def estimate(message, link, recipient_count, tariff):
    full_text = f'{message}\n{link}'.strip()
    segments = segment_count(full_text, tariff)
    return full_text, segments, Decimal(segments * recipient_count) * tariff.price_per_segment


@transaction.atomic
def reserve_campaign(campaign, user):
    campaign = SmsCampaign.objects.select_for_update().get(id=campaign.id, user=user)
    if campaign.status != SmsCampaign.READY_FOR_PAYMENT:
        return campaign, False, 'campaign_not_payable'
    wallet, _ = Wallet.objects.get_or_create(user=user)
    wallet = Wallet.objects.select_for_update().get(id=wallet.id)
    if wallet.balance < campaign.estimated_cost:
        return campaign, False, 'insufficient_wallet_balance'
    wallet.balance = F('balance') - campaign.estimated_cost
    wallet.save(update_fields=('balance', 'updated_at'))
    Transaction.objects.create(user=user, from_wallet=wallet, to_wallet=None,
                               action=f'sms_reserve:{campaign.id}', amount=campaign.estimated_cost)
    campaign.reserved_cost = campaign.estimated_cost
    campaign.status = SmsCampaign.QUEUED
    campaign.save(update_fields=('reserved_cost', 'status', 'updated_at'))
    return campaign, True, ''


@transaction.atomic
def refund_campaign(campaign, reason=''):
    campaign = SmsCampaign.objects.select_for_update().get(id=campaign.id)
    refund = campaign.reserved_cost - campaign.actual_cost
    if refund > 0:
        wallet = Wallet.objects.select_for_update().get(user=campaign.user)
        wallet.balance = F('balance') + refund
        wallet.save(update_fields=('balance', 'updated_at'))
        Transaction.objects.create(user=campaign.user, from_wallet=wallet, to_wallet=wallet,
                                   action=f'sms_refund:{campaign.id}', amount=refund)
    campaign.reserved_cost = campaign.actual_cost
    campaign.failure_reason = reason or campaign.failure_reason
    campaign.save(update_fields=('reserved_cost', 'failure_reason', 'updated_at'))
    return campaign


def send_campaign(campaign):
    campaign = SmsCampaign.objects.prefetch_related('recipients').select_related('line').get(id=campaign.id)
    changed = SmsCampaign.objects.filter(id=campaign.id, status=SmsCampaign.QUEUED).update(status=SmsCampaign.SENDING)
    if not changed:
        return campaign
    payload = {
        'lineNumber': campaign.line.number,
        'messageText': f'{campaign.message}\n{campaign.link}'.strip(),
        'mobiles': list(campaign.recipients.values_list('mobile_number', flat=True)),
        'sendDateTime': campaign.scheduled_at.isoformat() if campaign.scheduled_at else None,
    }
    try:
        result = SMSCoreHandler.send_bulk(payload)
    except Exception as exc:
        result = {'status': 0, 'message': str(exc), 'data': None}
    if result.get('status') != 1:
        reason = str(result.get('message') or 'provider_unavailable')[:1000]
        SmsCampaign.objects.filter(id=campaign.id).update(status=SmsCampaign.FAILED, failure_reason=reason)
        refund_campaign(campaign, reason)
        return SmsCampaign.objects.get(id=campaign.id)
    data = result.get('data') or {}
    campaign.recipients.update(status=SmsRecipient.SENT)
    SmsCampaign.objects.filter(id=campaign.id).update(
        status=SmsCampaign.SENT, actual_cost=campaign.estimated_cost,
        provider_pack_id=str(data.get('packId') or data.get('packID') or ''), sent_at=timezone.now(),
    )
    return SmsCampaign.objects.get(id=campaign.id)
