from django.db import transaction
from django.utils import timezone

from apps.product.models import ProductRevision
from apps.product.serializers.owner_serializers import ProductUpdateSerializer


@transaction.atomic
def review_product_revision(*, revision, reviewer, action, reason=''):
    """Review a pending product draft under a row lock."""
    revision = ProductRevision.objects.select_for_update().select_related('product').get(
        pk=revision.pk,
        status=ProductRevision.PENDING,
    )
    if action == 'approve':
        serializer = ProductUpdateSerializer(revision.product, data=revision.payload)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        revision.status = ProductRevision.APPROVED
    else:
        revision.status = ProductRevision.REJECTED

    revision.reviewed_by = reviewer
    revision.reviewed_at = timezone.now()
    revision.rejection_reason = reason
    revision.save(update_fields=[
        'status', 'reviewed_by', 'reviewed_at', 'rejection_reason', 'updated_at',
    ])
    return revision
