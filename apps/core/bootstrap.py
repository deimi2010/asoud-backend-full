from drf_spectacular.utils import extend_schema
from django.db.models import Prefetch, Q
from rest_framework import serializers, status, views
from rest_framework.response import Response

from apps.core.permissions import IsAuthenticatedUser
from apps.market.models import Market, MarketMembership
from utils.response import ApiResponse


class BootstrapMarketSerializer(serializers.ModelSerializer):
    access = serializers.SerializerMethodField()

    class Meta:
        model = Market
        fields = ('id', 'business_id', 'name', 'status', 'access')
        read_only_fields = fields

    def get_access(self, obj) -> str:
        if obj.user_id == self.context['user'].id:
            return 'owner'
        membership = getattr(obj, 'current_membership', None)
        return membership[0].role if membership else None


class BootstrapCapabilitiesSerializer(serializers.Serializer):
    create_market = serializers.BooleanField()
    buy = serializers.BooleanField()
    use_business_card = serializers.BooleanField()
    manage_platform = serializers.BooleanField()


class AppBootstrapDataSerializer(serializers.Serializer):
    user_id = serializers.UUIDField()
    is_platform_admin = serializers.BooleanField()
    capabilities = BootstrapCapabilitiesSerializer()
    markets = BootstrapMarketSerializer(many=True)


class AppBootstrapEnvelopeSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    code = serializers.IntegerField()
    data = AppBootstrapDataSerializer()


class AppBootstrapView(views.APIView):
    """Return stable post-login routing and capability data for the client."""

    permission_classes = [IsAuthenticatedUser]

    @extend_schema(
        responses={200: AppBootstrapEnvelopeSerializer},
        tags=['Application bootstrap'],
    )
    def get(self, request):
        membership_query = MarketMembership.objects.filter(
            user=request.user,
            is_active=True,
        )
        markets = Market.objects.filter(
            Q(user=request.user) | Q(memberships__in=membership_query)
        ).distinct().order_by('created_at', 'id').prefetch_related(
            Prefetch(
                'memberships',
                queryset=membership_query,
                to_attr='current_membership',
            )
        )
        is_admin = bool(request.user.is_staff and request.user.is_active)
        data = {
            'user_id': request.user.id,
            'is_platform_admin': is_admin,
            'capabilities': {
                'create_market': True,
                'buy': True,
                'use_business_card': True,
                'manage_platform': is_admin,
            },
            'markets': BootstrapMarketSerializer(
                markets,
                many=True,
                context={'user': request.user},
            ).data,
        }
        return Response(
            ApiResponse(success=True, code=status.HTTP_200_OK, data=data)
        )
