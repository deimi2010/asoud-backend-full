from rest_framework import views, status, permissions
from rest_framework.response import Response
from utils.response import ApiResponse
from apps.market.models import Market
from apps.market.serializers.user_serializers import MarketListSerializer
from apps.product.models import Product
from apps.flutter.serializers import PublicProductDetailSerializer
from apps.referral.access import viewable_markets

# Create your views here.
class MarketDetailView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, market_id=None):
        market_identifier = market_id or request.get_host().split('.')[0]

        try:
            market = viewable_markets(request.user).get(
                business_id=market_identifier,
                status=Market.PUBLISHED,
            )
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

        return Response(
            ApiResponse(
                success=True,
                code=200,
                data=serializer.data
            )
        )
class ProductListView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, market_id=None):
        market_identifier = market_id or request.get_host().split('.')[0]

        try:
            market = viewable_markets(request.user).get(
                business_id=market_identifier,
                status=Market.PUBLISHED,
            )
        except Market.DoesNotExist:
            return Response(
                ApiResponse(
                    success=False,
                    code=404,
                    error="Market Not Found"
                ),
                status=status.HTTP_404_NOT_FOUND
            )
        
        products = Product.objects.filter(market=market, status=Product.PUBLISHED)
        
        serializer = PublicProductDetailSerializer(
            products, many=True, context={'request': request}
        )

        return Response(
            ApiResponse(
                success=True,
                code=200,
                data=serializer.data
            )
        )


class ProductDetailView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk, market_id=None):
        market_identifier = market_id or request.get_host().split('.')[0]
        
        try:
            product = Product.objects.get(id=pk, status=Product.PUBLISHED)
        except Product.DoesNotExist:
            return Response(
                ApiResponse(
                    success=False,
                    code=404,
                    error="Product Not Found"
                ),
                status=status.HTTP_404_NOT_FOUND
            )

        try:
            market = viewable_markets(request.user).get(
                business_id=market_identifier,
                status=Market.PUBLISHED,
            )
        except Market.DoesNotExist:
            return Response(
                ApiResponse(
                    success=False,
                    code=404,
                    error="Market Not Found"
                ),
                status=status.HTTP_404_NOT_FOUND
            )
        
        if product.market != market:
            return Response(
                ApiResponse(
                    success=False,
                    code=400,
                    error="Product and Market Mismatch"
                ),
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = PublicProductDetailSerializer(
            product, context={'request': request}
        )

        return Response(
            ApiResponse(
                success=True,
                code=200,
                data=serializer.data
            )
        )
