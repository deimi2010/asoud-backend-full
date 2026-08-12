from rest_framework import views, status, permissions
from rest_framework.response import Response
from django.db import transaction
from django.db.models.deletion import ProtectedError
from utils.response import ApiResponse
from apps.product.models import Product
from apps.product.serializers.owner_serializers import (
    ProductDetailSerializer,
    ProductListSerializer
)
from apps.affiliate.serializers.user import (
    AffiliateProductCreateSerializer,
    AffiliateProductDetailSerializer,
    AffiliateProductListSerializer,
    AffiliateProductThemeCreateSerializer,
    AffiliateProductThemeListSerializer
)
from apps.affiliate.models import (
    AffiliateProduct,
    AffiliateProductTheme
)
from apps.market.models import Market

class ProductsForAffiliateListView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        products = Product.objects.filter(
            is_marketer=True, 
            status=Product.PUBLISHED,
            market__status=Market.PUBLISHED,
        ).select_related('market', 'sub_category')

        if price_lt := request.GET.get('price_lt'):
            products = products.filter(main_price__lte=price_lt)
        
        if price_gt := request.GET.get('price_gt'):
            products = products.filter(main_price__gte=price_gt)

        if type := request.GET.get('type'):
            products = products.filter(type=type)
        
        order_by = request.GET.get('order_by')
        if order_by in ['main_price', '-main_price', 'created_at', '-created_at']:
            products = products.order_by(order_by)
        
        serializer = ProductListSerializer(products, many=True)

        return Response(
            ApiResponse(
                success=True,
                code=200,
                data=serializer.data
            )
        )

class AffiliateProductDetailBeforeCreateView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, pk):
        try:
            product = Product.objects.get(
                id=pk,
                is_marketer=True,
                status=Product.PUBLISHED,
                market__status=Market.PUBLISHED,
            )
        except Product.DoesNotExist:
            return Response(
                ApiResponse(
                    success=False,
                    code=404,
                    error="Product Not Found"
                ),
                status=status.HTTP_404_NOT_FOUND,
            )
        
        serializer = ProductDetailSerializer(product)

        return Response(
            ApiResponse(
                success=True,
                code=200,
                data=serializer.data
            )
        )

class AffiliateProductCreateView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        serializer = AffiliateProductCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            market = Market.objects.select_for_update().get(
                id=serializer.validated_data['market'].id,
                user=request.user,
                status=Market.PUBLISHED,
            )
        except Market.DoesNotExist:
            return Response(
                ApiResponse(success=False, code=403, error="Permission denied"),
                status=status.HTTP_403_FORBIDDEN,
            )
        try:
            product = Product.objects.get(
                id=serializer.validated_data['product'].id,
                is_marketer=True,
                status=Product.PUBLISHED,
                market__status=Market.PUBLISHED,
            )
        except Product.DoesNotExist:
            return Response(
                ApiResponse(
                    success=False,
                    code=400,
                    error="Product is not available for affiliate marketing",
                ),
                status=status.HTTP_400_BAD_REQUEST,
            )
        if AffiliateProduct.objects.filter(market=market, product=product).exists():
            return Response(
                ApiResponse(success=False, code=409, error="Affiliate product already exists"),
                status=status.HTTP_409_CONFLICT,
            )

        obj = serializer.save(
            market=market,
            product=product,
            type=product.type,
            sub_category=product.sub_category,
            status=AffiliateProduct.DRAFT,
        )

        serialized_data = AffiliateProductDetailSerializer(obj).data
        
        return Response(
            ApiResponse(
                success=True,
                code=201,
                data=serialized_data
            ),
            status=status.HTTP_201_CREATED,
        )

class AffiliateProductsListView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, pk):
        try:
            market = Market.objects.get(id=pk, user=request.user)

            products = AffiliateProduct.objects.filter(
                market=market
            )

            serializer = AffiliateProductListSerializer(products, many=True)

            return Response(
                ApiResponse(
                    success=True,
                    code=200,
                    data=serializer.data
                )
            )

        except Market.DoesNotExist:
            return Response(
                ApiResponse(
                    success=False,
                    code=404,
                    error="Market Not Found",
                ),
                status=status.HTTP_404_NOT_FOUND,
            )

class AffiliateProductDetailView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, pk):
        try:
            product = AffiliateProduct.objects.get(id=pk, market__user=request.user)
        except AffiliateProduct.DoesNotExist:
            return Response(
                ApiResponse(
                    success=False,
                    code=404,
                    error="Affiliate Product Not Found"
                ),
                status=status.HTTP_404_NOT_FOUND,
            )
        
        serializer = AffiliateProductDetailSerializer(product)

        return Response(
            ApiResponse(
                success=True,
                code=200,
                data=serializer.data
            )
        )

class AffiliateProductUpdateView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def put(self, request, pk):
        try:
            product = AffiliateProduct.objects.select_for_update().get(
                id=pk,
                market__user=request.user,
            )
        except AffiliateProduct.DoesNotExist:
            return Response(
                ApiResponse(
                    success=False,
                    code=404,
                    error="Affiliate Product Not Found",
                ),
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = AffiliateProductCreateSerializer(
            product,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        for field in ('market', 'product'):
            requested = serializer.validated_data.get(field)
            if requested is not None and requested.pk != getattr(product, f'{field}_id'):
                return Response(
                    ApiResponse(
                        success=False,
                        code=400,
                        error=f'{field} cannot be changed after creation',
                    ),
                    status=status.HTTP_400_BAD_REQUEST,
                )
            serializer.validated_data.pop(field, None)

        obj = serializer.save()
        return Response(
            ApiResponse(
                success=True,
                code=200,
                data=AffiliateProductDetailSerializer(obj).data,
            )
        )

class AffiliateProductDeleteView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def delete(self, request, pk):
        try:
            product = AffiliateProduct.objects.select_for_update().get(
                id=pk,
                market__user=request.user,
            )
            product.delete()

            return Response(
                ApiResponse(
                    success=True,
                    code=204
                ),
                status=status.HTTP_204_NO_CONTENT
            )

        except AffiliateProduct.DoesNotExist:
            return Response(
                ApiResponse(
                    success=False,
                    code=404,
                    error="Affiliate Product Not Found",
                ),
                status=status.HTTP_404_NOT_FOUND,
            )
        except ProtectedError:
            return Response(
                ApiResponse(
                    success=False,
                    code=409,
                    error="Affiliate product is referenced by order history",
                ),
                status=status.HTTP_409_CONFLICT,
            )

class AffiliateProductThemeCreateAPIView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def post(self, request, pk):
        try:
            market = Market.objects.select_for_update().get(id=pk, user=request.user)
        except Market.DoesNotExist:
            return Response(
                ApiResponse(
                    success=False,
                    code=404,
                    error="Market Not Found"
                ),
                status=status.HTTP_404_NOT_FOUND,
            )
        
        serializer = AffiliateProductThemeCreateSerializer(
            data=request.data,
            context={'request': request},
        )

        if serializer.is_valid(raise_exception=True):
            serializer.save(
                market=market,
            )

            success_response = ApiResponse(
                success=True,
                code=200,
                data={
                    **serializer.data,
                },
                message='Affiliate Product theme created successfully.',
            )

            return Response(success_response, status=status.HTTP_201_CREATED)

class AffiliateProductThemeListAPIView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, pk):
        try:
            market = Market.objects.get(id=pk, user=request.user)
        except Market.DoesNotExist:
            return Response(
                ApiResponse(
                    success=False,
                    code=404,
                    error="Market Not Found"
                ),
                status=status.HTTP_404_NOT_FOUND,
            )
    
        product_theme_list = AffiliateProductTheme.objects.filter(market=market)

        serializer = AffiliateProductThemeListSerializer(
            product_theme_list,
            many=True,
            context={"request": request},
        )

        success_response = ApiResponse(
            success=True,
            code=200,
            data=serializer.data,
            message='Data retrieved successfully'
        )

        return Response(success_response)

class AffiliateProductThemeUpdateAPIView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    @transaction.atomic
    def put(self, request, pk):
        try:
            product_theme = AffiliateProductTheme.objects.get(
                id=pk,
                market__user=request.user,
            )
        except AffiliateProductTheme.DoesNotExist:
            return Response(
                ApiResponse(
                    success=False,
                    code=404,
                    error="Affiliate Product Theme Not Found"
                ),
                status=status.HTTP_404_NOT_FOUND,
            )
        products = request.data.get("products", [])

        if not isinstance(products, list):
            response = ApiResponse(
                success=False,
                code=400,
                error={
                    'code': 'bad_request',
                    'detail': 'Invalid format. "products" should be a list.',
                }
            )
            return Response(response, status=status.HTTP_400_BAD_REQUEST)

        AffiliateProduct.objects.filter(
            id__in=products,
            market=product_theme.market,
        ).update(theme=product_theme)
            
        success_response = ApiResponse(
            success=True,
            code=200,
            data={},
            message='Affiliate Product theme updated successfully.',
        )
        return Response(success_response, status=status.HTTP_200_OK)


