from rest_framework import views, status, permissions
from rest_framework.response import Response
from utils.response import ApiResponse
from apps.market.models import Market
from apps.market.serializers.user_serializers import MarketListSerializer
from apps.product.models import Product
from apps.product.serializers.owner_serializers import (
    ProductDetailSerializer,
    ProductListSerializer    
)

# Create your views here.
class MarketDetailView(views.APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request): 
        host = request.get_host()
        market_identifier = host.split('.')[0]
        
        try:
            market = Market.objects.get(business_id=market_identifier)
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
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        host = request.get_host()
        market_identifier = host.split('.')[0]

        try:
            market = Market.objects.get(business_id=market_identifier)
        except Market.DoesNotExist:
            return Response(
                ApiResponse(
                    success=False,
                    code=404,
                    error="Market Not Found"
                ),
                status=status.HTTP_404_NOT_FOUND
            )
        
        products = Product.objects.filter(market=market)
        
        serializer = ProductListSerializer(products, many=True)

        return Response(
            ApiResponse(
                success=True,
                code=200,
                data=serializer.data
            )
        )


class ProductDetailView(views.APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, pk):
        host = request.get_host()
        market_identifier = host.split('.')[0]
        
        try:
            product = Product.objects.get(id=pk)
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
            market = Market.objects.get(business_id=market_identifier)
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
        
        serializer = ProductDetailSerializer(product)

        return Response(
            ApiResponse(
                success=True,
                code=200,
                data=serializer.data
            )
        )
        