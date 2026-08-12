"""Read-only Analytics v2 API."""

from rest_framework import permissions, serializers, status
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.market.models import Market
from apps.product.models import Product

from .models import AnalyticsEvent, UserSession
from .services import AnalyticsService, MLService


def _days(request, default=30):
    try:
        return max(1, min(int(request.query_params.get('days', default)), 366))
    except (TypeError, ValueError):
        return default


class IsStaff(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_staff)


class AnalyticsEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnalyticsEvent
        fields = [
            'id', 'user', 'session', 'session_key', 'event_type', 'product',
            'market', 'order', 'dedupe_key', 'metadata', 'occurred_at',
        ]
        read_only_fields = fields


class UserSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserSession
        fields = [
            'id', 'user', 'session_key', 'started_at', 'last_seen_at',
            'ended_at', 'duration', 'is_active', 'device_type',
        ]
        read_only_fields = fields


class PlatformDashboardView(APIView):
    permission_classes = [IsStaff]

    def get(self, request):
        return Response(AnalyticsService().dashboard(days=_days(request)))


class PlatformTimeSeriesView(APIView):
    permission_classes = [IsStaff]

    def get(self, request):
        return Response(AnalyticsService().time_series(days=_days(request)))


class PlatformTopProductsView(APIView):
    permission_classes = [IsStaff]

    def get(self, request):
        return Response(AnalyticsService().top_products(days=_days(request)))


class PlatformTopMarketsView(APIView):
    permission_classes = [IsStaff]

    def get(self, request):
        return Response(AnalyticsService().top_markets(days=_days(request)))


class AnalyticsEventListView(ListAPIView):
    permission_classes = [IsStaff]
    serializer_class = AnalyticsEventSerializer
    queryset = AnalyticsEvent.objects.select_related('user', 'product', 'market', 'order')
    filterset_fields = ['event_type', 'user', 'product', 'market', 'order']


class UserSessionListView(ListAPIView):
    permission_classes = [IsStaff]
    serializer_class = UserSessionSerializer
    queryset = UserSession.objects.select_related('user')
    filterset_fields = ['user', 'is_active']


class OwnerScopeMixin:
    def market_ids(self, request):
        markets = Market.objects.filter(user=request.user)
        requested = request.query_params.get('market_id')
        if requested:
            markets = markets.filter(pk=requested)
            if not markets.exists():
                return None
        return list(markets.values_list('id', flat=True))

    def no_market_response(self):
        return Response(
            {'error': 'Owned market not found.', 'code': 'market_not_found'},
            status=status.HTTP_404_NOT_FOUND,
        )


class OwnerSummaryView(OwnerScopeMixin, APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        market_ids = self.market_ids(request)
        if market_ids is None:
            return self.no_market_response()
        return Response(AnalyticsService().dashboard(days=_days(request), market_ids=market_ids))


class OwnerTimeSeriesView(OwnerScopeMixin, APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        market_ids = self.market_ids(request)
        if market_ids is None:
            return self.no_market_response()
        return Response(AnalyticsService().time_series(days=_days(request), market_ids=market_ids))


class OwnerProductsView(OwnerScopeMixin, APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        market_ids = self.market_ids(request)
        if market_ids is None:
            return self.no_market_response()
        return Response(AnalyticsService().top_products(days=_days(request), market_ids=market_ids))


class OwnerProductForecastView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, product_id):
        try:
            product = Product.objects.get(pk=product_id, market__user=request.user)
        except Product.DoesNotExist:
            return Response(
                {'error': 'Owned product not found.', 'code': 'product_not_found'},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(MLService().demand_forecast(product, _days(request, 7)))


class ProductRecommendationsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response({'products': MLService().get_product_recommendations(
            request.user,
            request.query_params.get('limit', 10),
        )})


class SimilarProductsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, product_id):
        try:
            product = Product.objects.get(
                pk=product_id,
                status=Product.PUBLISHED,
                market__status=Market.PUBLISHED,
            )
        except Product.DoesNotExist:
            return Response(
                {'error': 'Published product not found.', 'code': 'product_not_found'},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response({'products': MLService().get_similar_products(
            product,
            request.query_params.get('limit', 10),
        )})


class DashboardView(APIView):
    """Compatibility dashboard route with explicit staff/owner scoping."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        service = AnalyticsService()
        if request.user.is_staff:
            return Response(service.dashboard(days=_days(request)))
        market_ids = list(Market.objects.filter(user=request.user).values_list('id', flat=True))
        return Response(service.dashboard(days=_days(request), market_ids=market_ids))
