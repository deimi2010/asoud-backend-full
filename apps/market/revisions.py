from apps.market.models import MarketRevision


def json_payload(validated_data):
    result = {}
    for key, value in validated_data.items():
        if hasattr(value, 'pk'):
            result[key] = str(value.pk)
        elif hasattr(value, 'as_tuple'):
            result[key] = str(value)
        else:
            result[key] = value
    return result


def save_pending_section(*, market, user, section, data):
    revision = MarketRevision.objects.filter(
        market=market,
        status=MarketRevision.PENDING,
    ).first()
    payload = dict(revision.payload) if revision else {}
    payload[section] = json_payload(data)
    if revision is None:
        revision = MarketRevision.objects.create(
            market=market,
            created_by=user,
            payload=payload,
        )
    else:
        revision.created_by = user
        revision.payload = payload
        revision.reviewed_by = None
        revision.reviewed_at = None
        revision.rejection_reason = ''
        revision.save(update_fields=[
            'created_by', 'payload', 'reviewed_by', 'reviewed_at',
            'rejection_reason', 'updated_at',
        ])
    return revision
