from django.shortcuts import get_object_or_404
from rest_framework import serializers, views
from rest_framework.response import Response

from apps.core.permissions import IsPlatformAdmin
from apps.market.models import Market, MarketRevision
from apps.market.services import review_market_publication, review_market_revision


class RevisionDecisionSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=('approve', 'reject'))
    reason = serializers.CharField(required=False, allow_blank=True, default='')


class PublicationDecisionSerializer(serializers.Serializer):
    action = serializers.ChoiceField(
        choices=('approve', 'reject', 'request_changes')
    )
    reason = serializers.CharField(required=False, allow_blank=True, default='')

    def validate(self, attrs):
        if attrs['action'] in ('reject', 'request_changes') and not attrs['reason'].strip():
            raise serializers.ValidationError(
                {'reason': 'A reason is required for rejection or requested changes.'}
            )
        return attrs


class EmptyRequestSerializer(serializers.Serializer):
    pass


class MarketRevisionListAdminView(views.APIView):
    permission_classes = [IsPlatformAdmin]
    serializer_class = RevisionDecisionSerializer

    def get(self, request):
        revisions = MarketRevision.objects.filter(
            status=MarketRevision.PENDING,
        ).select_related('market', 'created_by')
        return Response([
            {
                'id': str(revision.id),
                'market_id': str(revision.market_id),
                'market_name': revision.market.name,
                'payload': revision.payload,
                'created_at': revision.created_at,
            }
            for revision in revisions
        ])

class MarketRevisionDecisionAdminView(views.APIView):
    permission_classes = [IsPlatformAdmin]
    serializer_class = RevisionDecisionSerializer

    def post(self, request, pk):
        decision = RevisionDecisionSerializer(data=request.data)
        decision.is_valid(raise_exception=True)
        revision = get_object_or_404(
            MarketRevision.objects.select_related('market'),
            pk=pk,
            status=MarketRevision.PENDING,
        )
        revision = review_market_revision(
            revision=revision,
            reviewer=request.user,
            action=decision.validated_data['action'],
            reason=decision.validated_data['reason'],
        )
        return Response({'id': str(revision.id), 'status': revision.status})


class MarketPublicationAdminView(views.APIView):
    permission_classes = [IsPlatformAdmin]
    serializer_class = PublicationDecisionSerializer

    def post(self, request, market_id):
        decision = PublicationDecisionSerializer(data=request.data)
        decision.is_valid(raise_exception=True)
        market = get_object_or_404(
            Market.objects.all(),
            pk=market_id,
        )
        market, commissions = review_market_publication(
            market=market,
            reviewer=request.user,
            action=decision.validated_data['action'],
            reason=decision.validated_data['reason'],
        )
        return Response({
            'market_id': str(market.id),
            'status': market.status,
            'commission_count': len(commissions),
        })


class MarketReactivateAdminView(views.APIView):
    permission_classes = [IsPlatformAdmin]
    serializer_class = EmptyRequestSerializer

    def post(self, request, market_id):
        market = get_object_or_404(Market.objects.all(), pk=market_id)
        if market.status != Market.INACTIVE:
            raise serializers.ValidationError(
                {'status': 'Only an inactive store can be reactivated.'}
            )
        market.status = Market.DRAFT
        market.status_reason = ''
        market.save(update_fields=['status', 'status_reason', 'updated_at'])
        return Response({'market_id': str(market.id), 'status': market.status})
