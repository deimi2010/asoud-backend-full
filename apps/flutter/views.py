from rest_framework import views, status, permissions
from rest_framework.response import Response
from drf_spectacular.utils import OpenApiResponse, extend_schema
from utils.response import ApiResponse
from apps.core.base_views import BaseDetailView

from apps.market.models import Market
from apps.market.serializers.user_serializers import (
    MarketListSerializer,
    MarketDetailSerializer
)
from apps.product.models import Product, ProductTheme
from apps.product.serializers.owner_serializers import (
    ProductThemeListSerializer,
)
from apps.flutter.serializers import (
    ProductDetailQuerySerializer,
    PublicProductDetailEnvelopeSerializer,
    PublicProductDetailSerializer,
)
from apps.advertise.models import Advertisement
from apps.advertise.serializers import AdvertiseSerializer
from apps.advertise.core import public_advertisements
from apps.users.models import UserBankInfo
from apps.users.serializers import PublicUserBankInfoSerializer
from apps.analytics.models import AnalyticsEvent
from apps.analytics.services import AnalyticsRecorder
# Create your views here.


class MarketDetailView(views.APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        market_id = request.GET.get('id')
        if not market_id:
            return Response(
                ApiResponse(
                    success=False,
                    code=400,
                    error="Market Id Not Provided"
                ),
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            market = Market.objects.get(id=market_id)
        except Market.DoesNotExist:
            return Response(
                ApiResponse(
                    success=False,
                    code=404,
                    error="Market Not Found"
                ),
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = MarketListSerializer(market)
        AnalyticsRecorder.record_request(
            request,
            AnalyticsEvent.MARKET_VIEW,
            market=market,
        )
        return Response(
            ApiResponse(
                success=True,
                code=200,
                data=serializer.data
            )
        )
        

class ProductDetailView(views.APIView):
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        parameters=[ProductDetailQuerySerializer],
        responses={
            200: PublicProductDetailEnvelopeSerializer,
            400: OpenApiResponse(description='Invalid or missing product UUID.'),
            404: OpenApiResponse(description='Published product not found.'),
        },
    )
    def get(self, request):
        query = ProductDetailQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)

        try:
            product = (
                Product.objects.select_related(
                    'market',
                    'required_product__market',
                    'gift_product__market',
                )
                .prefetch_related('keywords', 'images', 'ships')
                .get(
                    id=query.validated_data['id'],
                    status=Product.PUBLISHED,
                    market__status=Market.PUBLISHED,
                )
            )
        except Product.DoesNotExist:
            return Response(
                ApiResponse(
                    success=False,
                    code=404,
                    error={
                        'code': 'product_not_found',
                        'detail': 'Published product not found',
                    },
                ),
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = PublicProductDetailSerializer(
            product,
            context={'request': request},
        )
        AnalyticsRecorder.record_request(
            request,
            AnalyticsEvent.PRODUCT_VIEW,
            product=product,
            market=product.market,
        )

        return Response(
            ApiResponse(
                success=True,
                code=200,
                data=serializer.data
            )
        )


class AdvertizeDetailView(views.APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        ad_id = request.GET.get('id')
        if not ad_id:
            return Response(
                ApiResponse(
                    success=False,
                    code=400,
                    error="Advertisement Id Not Provided"
                ),
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            ad = public_advertisements().get(id=ad_id)
        except Advertisement.DoesNotExist:
            return Response(
                ApiResponse(
                    success=False,
                    code=404,
                    error="Advertisement Not Found"
                ),
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = AdvertiseSerializer(ad)

        return Response(
            ApiResponse(
                success=True,
                code=200,
                data=serializer.data
            )
        )


class VisitCardView(BaseDetailView):
    """
    Get market visit card details
    """
    permission_classes = [permissions.AllowAny]
    
    def get_queryset(self):
        return Market.objects.select_related(
            'sub_category',
            'location',
            'contact'
        ).prefetch_related(
            'viewed_by'
        )
    
    def get_serializer_class(self):
        return MarketDetailSerializer

    def get(self, request, business_id):
        try:
            market = self.get_queryset().get(business_id=business_id)
            serializer = MarketDetailSerializer(market)
            AnalyticsRecorder.record_request(
                request,
                AnalyticsEvent.MARKET_VIEW,
                market=market,
            )
            return self.success_response(data=serializer.data)
        
        except Market.DoesNotExist:
            return self.error_response("Market not found", 404)
        except Exception as e:
            return self.error_response(f"Error retrieving market: {str(e)}", 500)
        

class BankCardView(BaseDetailView):
    """
    Get bank card information
    """
    permission_classes = [permissions.AllowAny]
    
    def get_queryset(self):
        return UserBankInfo.objects.select_related('bank_info')
    
    def get_serializer_class(self):
        return PublicUserBankInfoSerializer

    def get(self, request, pk):
        try:
            bank_info = self.get_queryset().get(id=pk)
            serializer = PublicUserBankInfoSerializer(bank_info)
            response = self.success_response(data=serializer.data)
            response['Cache-Control'] = 'private, no-store'
            return response
        
        except UserBankInfo.DoesNotExist:
            return self.error_response("Bank info not found", 404)


class MarketProductThemesView(views.APIView):
    """Public product themes of a market, for buyer-side store pages.

    The owner theme endpoints enforce ownership, so the mobile app had no
    way to render another user's store.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        market_id = request.GET.get('id')
        if not market_id:
            return Response(
                ApiResponse(
                    success=False,
                    code=400,
                    error="Market Id Not Provided"
                ),
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            market = Market.objects.get(id=market_id)
        except Market.DoesNotExist:
            return Response(
                ApiResponse(
                    success=False,
                    code=404,
                    error="Market Not Found"
                ),
                status=status.HTTP_404_NOT_FOUND
            )

        themes = ProductTheme.objects.filter(market=market)
        serializer = ProductThemeListSerializer(
            themes,
            many=True,
            context={"request": request},
        )
        return Response(
            ApiResponse(
                success=True,
                code=200,
                data=serializer.data
            )
        )
