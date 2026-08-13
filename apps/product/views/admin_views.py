from django.shortcuts import get_object_or_404
from rest_framework import serializers, views
from rest_framework.response import Response

from apps.core.permissions import IsPlatformAdmin
from apps.product.models import ProductRevision
from apps.product.services import review_product_revision


class ProductRevisionDecisionSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=('approve', 'reject'))
    reason = serializers.CharField(required=False, allow_blank=True, default='')


class ProductRevisionListAdminView(views.APIView):
    permission_classes = [IsPlatformAdmin]
    serializer_class = ProductRevisionDecisionSerializer

    def get(self, request):
        revisions = ProductRevision.objects.filter(status=ProductRevision.PENDING)
        return Response([
            {'id': str(row.id), 'product_id': str(row.product_id), 'payload': row.payload}
            for row in revisions
        ])

class ProductRevisionDecisionAdminView(views.APIView):
    permission_classes = [IsPlatformAdmin]
    serializer_class = ProductRevisionDecisionSerializer

    def post(self, request, pk):
        decision = ProductRevisionDecisionSerializer(data=request.data)
        decision.is_valid(raise_exception=True)
        revision = get_object_or_404(
            ProductRevision,
            pk=pk,
            status=ProductRevision.PENDING,
        )
        revision = review_product_revision(
            revision=revision,
            reviewer=request.user,
            action=decision.validated_data['action'],
            reason=decision.validated_data['reason'],
        )
        return Response({'id': str(revision.id), 'status': revision.status})
