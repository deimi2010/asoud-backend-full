from rest_framework import views, status, permissions
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema
from django.db import transaction
from django.db.models.deletion import ProtectedError
from utils.response import ApiResponse
from apps.product.models import Product
from apps.product.serializers.owner_serializers import (
    ProductDetailSerializer,
    ProductListSerializer
)
from apps.affiliate.serializers.user import (
    AffiliateBankProductSerializer,
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
from apps.market.access import accessible_markets


def _affiliate_markets(user, *, published=True):
    markets = accessible_markets(user, write=True).filter(
        sales_channel=Market.AFFILIATE,
    )
    return markets.filter(status=Market.PUBLISHED) if published else markets

class ProductsForAffiliateListView(views.APIView):
    serializer_class = ProductListSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        if not _affiliate_markets(request.user).exists():
            return Response(
                ApiResponse(success=False, code=403, error='An approved affiliate store is required'),
                status=status.HTTP_403_FORBIDDEN,
            )
        products = Product.objects.filter(
            is_marketer=True, 
            status=Product.PUBLISHED,
            market__status=Market.PUBLISHED,
            marketer_price__isnull=False,
            maximum_sell_price__isnull=False,
        ).exclude(market__user=request.user).select_related(
            'market', 'sub_category',
        ).prefetch_related('images')

        if price_lt := request.GET.get('price_lt'):
            products = products.filter(main_price__lte=price_lt)
        
        if price_gt := request.GET.get('price_gt'):
            products = products.filter(main_price__gte=price_gt)

        if type := request.GET.get('type'):
            products = products.filter(type=type)
        
        order_by = request.GET.get('order_by')
        if order_by in ['main_price', '-main_price', 'created_at', '-created_at']:
            products = products.order_by(order_by)
        
        serializer = AffiliateBankProductSerializer(
            products, many=True, context={'request': request},
        )

        return Response(
            ApiResponse(
                success=True,
                code=200,
                data=serializer.data
            )
        )

class AffiliateProductDetailBeforeCreateView(views.APIView):
    serializer_class = ProductDetailSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, pk):
        if not _affiliate_markets(request.user).exists():
            return Response(
                ApiResponse(success=False, code=403, error='An approved affiliate store is required'),
                status=status.HTTP_403_FORBIDDEN,
            )
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
        
        serializer = AffiliateBankProductSerializer(product, context={'request': request})

        return Response(
            ApiResponse(
                success=True,
                code=200,
                data=serializer.data
            )
        )

class AffiliateProductCreateView(views.APIView):
    serializer_class = AffiliateProductCreateSerializer
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        serializer = AffiliateProductCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            market = Market.objects.select_for_update().get(
                id=serializer.validated_data['market'].id,
                id__in=_affiliate_markets(request.user).values('id'),
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
        if product.market.user_id == request.user.id:
            return Response(
                ApiResponse(success=False, code=400, error='You cannot market your own product'),
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
            technical_detail=product.technical_detail,
            stock=product.stock,
            sell_type=product.sell_type,
            ship_cost=None,
            ship_cost_pay_type=product.ship_cost_pay_type,
            is_requirement=product.is_requirement,
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
    serializer_class = AffiliateProductListSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, pk):
        try:
            market = _affiliate_markets(request.user, published=False).get(id=pk)

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
    serializer_class = AffiliateProductDetailSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, pk):
        try:
            product = AffiliateProduct.objects.get(
                id=pk, market_id__in=_affiliate_markets(request.user, published=False).values('id')
            )
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
    serializer_class = AffiliateProductCreateSerializer
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def put(self, request, pk):
        try:
            product = AffiliateProduct.objects.select_for_update().get(
                id=pk,
                market_id__in=_affiliate_markets(request.user, published=False).values('id'),
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

        obj = serializer.save(status=AffiliateProduct.DRAFT)
        return Response(
            ApiResponse(
                success=True,
                code=200,
                data=AffiliateProductDetailSerializer(obj).data,
            )
        )


class AffiliateProductSubmitView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        request=None,
        responses={200: AffiliateProductDetailSerializer},
        tags=['Affiliate - User'],
    )
    @transaction.atomic
    def post(self, request, pk):
        try:
            product = AffiliateProduct.objects.select_for_update().get(
                id=pk,
                market_id__in=_affiliate_markets(
                    request.user, published=False,
                ).values('id'),
                status__in=(AffiliateProduct.DRAFT, AffiliateProduct.NEEDS_EDITING),
            )
        except AffiliateProduct.DoesNotExist:
            return Response(
                ApiResponse(success=False, code=404, error='Affiliate product not found'),
                status=status.HTTP_404_NOT_FOUND,
            )
        product.status = AffiliateProduct.QUEUE
        product.save(update_fields=('status', 'updated_at'))
        return Response(ApiResponse(
            success=True,
            code=200,
            data=AffiliateProductDetailSerializer(product).data,
            message='Affiliate product submitted for review',
        ))

class AffiliateProductDeleteView(views.APIView):
    serializer_class = AffiliateProductDetailSerializer
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def delete(self, request, pk):
        try:
            product = AffiliateProduct.objects.select_for_update().get(
                id=pk,
                market_id__in=_affiliate_markets(request.user, published=False).values('id'),
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
    serializer_class = AffiliateProductThemeCreateSerializer
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def post(self, request, pk):
        try:
            market = Market.objects.select_for_update().get(
                id=pk,
                id__in=_affiliate_markets(request.user, published=False).values('id'),
            )
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
    serializer_class = AffiliateProductThemeListSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, pk):
        try:
            market = _affiliate_markets(request.user, published=False).get(id=pk)
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
    serializer_class = AffiliateProductThemeCreateSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    @transaction.atomic
    def put(self, request, pk):
        try:
            product_theme = AffiliateProductTheme.objects.get(
                id=pk,
                market_id__in=_affiliate_markets(request.user, published=False).values('id'),
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

