from rest_framework import serializers, views
from rest_framework.response import Response

from apps.core.permissions import IsPlatformAdmin
from apps.referral.models import ReferralCommission, ReferralLevel


class ReferralLevelSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReferralLevel
        fields = ('level', 'percentage', 'is_active')


class ReferralLevelListAdminView(views.APIView):
    permission_classes = [IsPlatformAdmin]
    serializer_class = ReferralLevelSerializer

    def get(self, request):
        return Response(ReferralLevelSerializer(ReferralLevel.objects.all(), many=True).data)

class ReferralLevelUpdateAdminView(views.APIView):
    permission_classes = [IsPlatformAdmin]
    serializer_class = ReferralLevelSerializer

    def put(self, request, level):
        instance = ReferralLevel.objects.filter(level=level).first()
        serializer = ReferralLevelSerializer(instance, data={**request.data, 'level': level})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class ReferralCommissionAdminView(views.APIView):
    permission_classes = [IsPlatformAdmin]
    serializer_class = ReferralLevelSerializer

    def get(self, request):
        rows = ReferralCommission.objects.select_related(
            'beneficiary', 'source_user', 'market', 'payment'
        ).order_by('-created_at')[:500]
        return Response([
            {
                'id': str(row.id),
                'beneficiary_id': str(row.beneficiary_id),
                'source_user_id': str(row.source_user_id),
                'market_id': str(row.market_id),
                'payment_id': str(row.payment_id),
                'level': row.level,
                'base_amount': row.base_amount,
                'percentage': row.percentage,
                'amount': row.amount,
                'status': row.status,
            }
            for row in rows
        ])


class CommissionStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=(ReferralCommission.PAID, ReferralCommission.CANCELED)
    )


class ReferralCommissionStatusAdminView(views.APIView):
    permission_classes = [IsPlatformAdmin]
    serializer_class = CommissionStatusSerializer

    def post(self, request, pk):
        serializer = CommissionStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        commission = ReferralCommission.objects.filter(pk=pk).first()
        if commission is None:
            return Response({'detail': 'Commission not found.'}, status=404)
        desired = serializer.validated_data['status']
        if commission.status == desired:
            return Response({'id': str(commission.id), 'status': commission.status})
        if commission.status != ReferralCommission.ACCRUED:
            raise serializers.ValidationError(
                {'status': 'Only accrued commissions can be finalized.'}
            )
        commission.status = desired
        commission.save(update_fields=['status', 'updated_at'])
        return Response({'id': str(commission.id), 'status': commission.status})
