from rest_framework import views, status, permissions
from rest_framework.response import Response
from drf_spectacular.utils import OpenApiResponse, extend_schema
from django.db import transaction

from utils.response import ApiResponse

from apps.product.serializers.owner_serializers import (
    ProductCreateSerializer,
    ProductUpdateSerializer,
    ProductCreateEnvelopeSerializer,
    ProductDetailSerializer,
    ProductDetailEnvelopeSerializer,
    ProductListSerializer,
    ProductThemeListSerializer,
    ProductThemeCreateSerializer,
    ProductThemeCreateEnvelopeSerializer,
    ProductThemeListEnvelopeSerializer,
    ProductThemeUpdateSerializer,
    ProductThemeUpdateEnvelopeSerializer,
    ProductShippingCreateSerializer,
    ProductShipListEnvelopeSerializer,
    ProductShipListSerializer
)
from apps.product.models import Product, ProductRevision, ProductTheme
from apps.market.models import Market
from apps.advertise.core  import AdvertisementCore

# affiliate products
from apps.affiliate.models import (
    AffiliateProduct,
)
from apps.affiliate.serializers.user import (
    AffiliateProductListSerializer
)

@extend_schema(
    summary="Create Product",
    description="Create a new product for the authenticated user's market. Requires market ownership verification.",
    request=ProductCreateSerializer,
    responses={
        201: OpenApiResponse(response=ProductCreateEnvelopeSerializer),
        400: OpenApiResponse(description='Validation error'),
        403: OpenApiResponse(description='Market ownership required'),
    },
    tags=['Products - Owner']
)
class ProductCreateAPIView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = ProductCreateSerializer(
            data=request.data,
            context={'request': request},
        )

        if serializer.is_valid(raise_exception=True):
            # Ownership check - verify market belongs to user
            market = serializer.validated_data.get('market')
            if not request.user.is_staff and market.user_id != request.user.id:
                return Response(
                    ApiResponse(
                        success=False,
                        code=403,
                        error={
                            'code': 'permission_denied',
                            'detail': 'You do not have permission to create products for this market',
                        }
                    ),
                    status=status.HTTP_403_FORBIDDEN,
                )
            
            product = serializer.save()

            product_id = product.id

            if product.is_requirement:
                AdvertisementCore.create_advertisement_for_product(product)


            success_response = ApiResponse(
                success=True,
                code=201,
                data={
                    'product': product_id,
                    **serializer.data,
                },
                message='Product created successfully.',
            )

            return Response(success_response, status=status.HTTP_201_CREATED)


class ProductDiscountCreateAPIView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        request=None,
        responses={409: OpenApiResponse(description='Legacy product discount disabled')},
        description=(
            'Disabled because this legacy record mutates the product base price and '
            'is not the discount ledger consumed by checkout.'
        ),
    )
    @transaction.atomic
    def post(self, request, pk):
        try:
            product = Product.objects.select_for_update().get(id=pk)
        except Product.DoesNotExist:
            return Response(
                ApiResponse(
                    success=False,
                    code=404,
                    error={
                        'code': 'product_not_found',
                        'detail': 'Product not found',
                    }
                ),
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Ownership check
        if not request.user.is_staff and product.market.user_id != request.user.id:
            return Response(
                ApiResponse(
                    success=False,
                    code=403,
                    error={
                        'code': 'permission_denied',
                        'detail': 'You do not have permission to modify this product',
                    }
                ),
                status=status.HTTP_403_FORBIDDEN,
            )

        return Response(
            ApiResponse(
                success=False,
                code=409,
                error={
                    'code': 'legacy_product_discount_disabled',
                    'detail': (
                        'Use the authoritative discount contract consumed by checkout; '
                        'legacy product discounts are disabled.'
                    ),
                },
            ),
            status=status.HTTP_409_CONFLICT,
        )
    
class ProductShippingCreateAPIView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        request=ProductShippingCreateSerializer,
        responses={409: OpenApiResponse(description='Shipping checkout contract unavailable')},
        description=(
            'Disabled until checkout can select a shipping option and snapshot its price.'
        ),
    )
    def post(self, request, pk):
        try:
            product = Product.objects.get(id=pk)
        except  Product.DoesNotExist:
            return Response(
                ApiResponse(
                    success=False,
                    code=404,
                    error={
                        'code': 'product_not_found',
                        'detail': 'Product not found',
                    }
                ),
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Ownership check
        if not request.user.is_staff and product.market.user_id != request.user.id:
            return Response(
                ApiResponse(
                    success=False,
                    code=403,
                    error={
                        'code': 'permission_denied',
                        'detail': 'You do not have permission to modify this product',
                    }
                ),
                status=status.HTTP_403_FORBIDDEN,
            )
        
        return Response(
            ApiResponse(
                success=False,
                code=409,
                error={
                    'code': 'shipping_contract_unavailable',
                    'detail': (
                        'Shipping options cannot be created until checkout can '
                        'select and snapshot their price.'
                    ),
                }
            ),
            status=status.HTTP_409_CONFLICT,
        )


class ProductShippingListAPIView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    @extend_schema(responses={200: ProductShipListEnvelopeSerializer})
    def get(self, request, pk):
        try:
            product = Product.objects.get(id=pk)
        except Product.DoesNotExist:
            return Response(
                ApiResponse(
                    success=False,
                    code=404,
                    error={
                        'code': 'product_not_found',
                        'detail': 'Product not found',
                    }
                ),
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Ownership check
        if not request.user.is_staff and product.market.user_id != request.user.id:
            return Response(
                ApiResponse(
                    success=False,
                    code=403,
                    error={
                        'code': 'permission_denied',
                        'detail': 'You do not have permission to view this product',
                    }
                ),
                status=status.HTTP_403_FORBIDDEN,
            )
        
        shipping_options = product.ships.all()
        serializer = ProductShipListSerializer(
            shipping_options,
            many=True,
            context={"request": request},
        )           
        success_response = ApiResponse(
            success=True,
            code=200,
            data=serializer.data,
            message='Data retrieved successfully'
        )
        return Response(success_response, status=status.HTTP_200_OK)

class ProductListAPIView(views.APIView):
    serializer_class = ProductListSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, pk):
        # Verify market ownership
        try:
            market = Market.objects.get(id=pk)
        except Market.DoesNotExist:
            return Response(
                ApiResponse(
                    success=False,
                    code=404,
                    error={
                        'code': 'market_not_found',
                        'detail': 'Market not found',
                    }
                ),
                status=status.HTTP_404_NOT_FOUND
            )
        
        if not request.user.is_staff and market.user_id != request.user.id:
            return Response(
                ApiResponse(
                    success=False,
                    code=403,
                    error={
                        'code': 'permission_denied',
                        'detail': 'You do not have permission to view this market products',
                    }
                ),
                status=status.HTTP_403_FORBIDDEN,
            )
        
        product_list = Product.objects.filter(
            market=pk
        ).select_related(
            'market',
            'sub_category',
            'theme',
            'required_product',
            'gift_product'
        ).prefetch_related(
            'keywords',
            'images',
            'comments'
        )

        serializer = ProductListSerializer(
            product_list,
            many=True,
            context={"request": request},
        )

        with_affiliate = request.GET.get('affiliate')

        if with_affiliate:
            affiliate_product_list = AffiliateProduct.objects.filter(
                market=pk
            )
            
            aff_serializer = AffiliateProductListSerializer(
                affiliate_product_list,
                many=True,
                context={"request": request},
            )

            success_response = ApiResponse(
                success=True,
                code=200,
                data=serializer.data + aff_serializer.data,
                message='Data retrieved successfully'
            )
            
        else:
            success_response = ApiResponse(
                success=True,
                code=200,
                data=serializer.data,
                message='Data retrieved successfully'
            )

        return Response(success_response, status=status.HTTP_200_OK)


class ProductDetailAPIView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(responses={200: ProductDetailEnvelopeSerializer})
    def get(self, request, pk):
        try:
            product = Product.objects.get(id=pk)
        except Product.DoesNotExist:
            return Response(
                ApiResponse(
                    success=False,
                    code=404,
                    error={
                        'code': 'product_not_found',
                        'detail': 'Product not found',
                    }
                ),
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Ownership check
        if not request.user.is_staff and product.market.user_id != request.user.id:
            return Response(
                ApiResponse(
                    success=False,
                    code=403,
                    error={
                        'code': 'permission_denied',
                        'detail': 'You do not have permission to view this product',
                    }
                ),
                status=status.HTTP_403_FORBIDDEN,
            )
        
        serializer = ProductDetailSerializer(
            product,
            context={"request": request},
        )

        success_response = ApiResponse(
            success=True,
            code=200,
            data=serializer.data,
            message='Data retrieved successfully',
        )

        return Response(success_response, status=status.HTTP_200_OK)


class ProductUpdateAPIView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ProductUpdateSerializer

    def put(self, request, pk):
        try:
            product = Product.objects.select_related('market').get(pk=pk)
        except Product.DoesNotExist:
            return Response({'detail': 'Product not found.'}, status=status.HTTP_404_NOT_FOUND)
        if not request.user.is_staff and product.market.user_id != request.user.id:
            return Response({'detail': 'Product not found.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = ProductUpdateSerializer(product, data=request.data)
        serializer.is_valid(raise_exception=True)
        if product.status == Product.PUBLISHED and not request.user.is_staff:
            payload = {}
            for key, value in serializer.validated_data.items():
                if key == 'keywords':
                    payload[key] = [item.name for item in value]
                elif hasattr(value, 'pk'):
                    payload[key] = str(value.pk)
                else:
                    payload[key] = str(value) if hasattr(value, 'as_tuple') else value
            revision, _ = ProductRevision.objects.update_or_create(
                product=product,
                status=ProductRevision.PENDING,
                defaults={'created_by': request.user, 'payload': payload},
            )
            return Response(
                {'revision_id': str(revision.id), 'status': revision.status, 'draft': payload},
                status=status.HTTP_202_ACCEPTED,
            )
        serializer.save()
        return Response(ProductUpdateSerializer(product).data)


class ProductThemeCreateAPIView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        request=ProductThemeCreateSerializer,
        responses={201: ProductThemeCreateEnvelopeSerializer},
    )
    def post(self, request, pk):
        try:
            market = Market.objects.get(id=pk)
        except Market.DoesNotExist:
            return Response(
                ApiResponse(
                    success=False,
                    code=404,
                    error={
                        'code': 'market_not_found',
                        'detail': 'Market not found',
                    }
                ),
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Ownership check
        if not request.user.is_staff and market.user_id != request.user.id:
            return Response(
                ApiResponse(
                    success=False,
                    code=403,
                    error={
                        'code': 'permission_denied',
                        'detail': 'You do not have permission to modify this market',
                    }
                ),
                status=status.HTTP_403_FORBIDDEN,
            )
        
        serializer = ProductThemeCreateSerializer(
            data=request.data,
            context={'request': request},
        )

        if serializer.is_valid(raise_exception=True):
            serializer.save(
                market=market,
            )

            success_response = ApiResponse(
                success=True,
                code=201,
                data={
                    **serializer.data,
                },
                message='Product theme created successfully.',
            )

            return Response(success_response, status=status.HTTP_201_CREATED)


class ProductThemeListAPIView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(responses={200: ProductThemeListEnvelopeSerializer})
    def get(self, request, pk):
        try:
            market = Market.objects.get(id=pk)
        except Market.DoesNotExist:
            return Response(
                ApiResponse(
                    success=False,
                    code=404,
                    error={
                        'code': 'market_not_found',
                        'detail': 'Market not found',
                    }
                ),
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Ownership check
        if not request.user.is_staff and market.user_id != request.user.id:
            return Response(
                ApiResponse(
                    success=False,
                    code=403,
                    error={
                        'code': 'permission_denied',
                        'detail': 'You do not have permission to view this market themes',
                    }
                ),
                status=status.HTTP_403_FORBIDDEN,
            )
    
        product_theme_list = ProductTheme.objects.filter(market=market)

        serializer = ProductThemeListSerializer(
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

        return Response(success_response, status=status.HTTP_200_OK)


class ProductThemeUpdateAPIView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        request=ProductThemeUpdateSerializer,
        responses={200: ProductThemeUpdateEnvelopeSerializer},
    )
    @transaction.atomic
    def put(self, request, pk):
        try:
            product_theme = ProductTheme.objects.select_for_update().select_related(
                'market'
            ).get(id=pk)
        except ProductTheme.DoesNotExist:
            return Response(
                ApiResponse(
                    success=False,
                    code=404,
                    error={
                        'code': 'product_theme_not_found',
                        'detail': 'Product theme not found',
                    }
                ),
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Ownership check
        if not request.user.is_staff and product_theme.market.user_id != request.user.id:
            return Response(
                ApiResponse(
                    success=False,
                    code=403,
                    error={
                        'code': 'permission_denied',
                        'detail': 'You do not have permission to modify this product theme',
                    }
                ),
                status=status.HTTP_403_FORBIDDEN,
            )
        
        input_serializer = ProductThemeUpdateSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)

        try:
            product = Product.objects.select_for_update().select_related('market').get(
                id=input_serializer.validated_data['product']
            )

            # Ownership check for product
            if not request.user.is_staff and product.market.user_id != request.user.id:
                return Response(
                    ApiResponse(
                        success=False,
                        code=403,
                        error={
                            'code': 'permission_denied',
                            'detail': 'You do not have permission to modify this product',
                        }
                    ),
                    status=status.HTTP_403_FORBIDDEN,
                )

            if product.market_id != product_theme.market_id:
                return Response(
                    ApiResponse(
                        success=False,
                        code=400,
                        error={
                            'code': 'product_theme_market_mismatch',
                            'detail': 'Product and theme must belong to the same market',
                        },
                    ),
                    status=status.HTTP_400_BAD_REQUEST,
                )

            product.theme = product_theme
            product.theme_index = str(input_serializer.validated_data['index'])
            product.save(update_fields=['theme', 'theme_index', 'updated_at'])
        except Product.DoesNotExist:
            fail_response = ApiResponse(
                success=False,
                code=404,
                error={
                    'code': 'product_not_found',
                    'detail': 'Product not found',
                }
            )
            return Response(
                fail_response, 
                status=status.HTTP_404_NOT_FOUND
            )

        success_response = ApiResponse(
            success=True,
            code=200,
            data={},
            message='Product theme updated successfully.',
        )
        return Response(success_response, status=status.HTTP_200_OK)

class ProductThemeDeleteAPIView(views.APIView):
    serializer_class = ProductThemeUpdateSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def delete(self, request, pk):
        try:
            product = Product.objects.get(id=pk)
        except Product.DoesNotExist:
            return Response(
                ApiResponse(
                    success=False,
                    code=404,
                    error={
                        'code': 'product_not_found',
                        'detail': 'Product not found',
                    }
                ),
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Ownership check
        if not request.user.is_staff and product.market.user_id != request.user.id:
            return Response(
                ApiResponse(
                    success=False,
                    code=403,
                    error={
                        'code': 'permission_denied',
                        'detail': 'You do not have permission to modify this product',
                    }
                ),
                status=status.HTTP_403_FORBIDDEN,
            )
        
        product.theme = None
        product.theme_index = None
        product.save(update_fields=['theme', 'theme_index', 'updated_at'])
            
        success_response = ApiResponse(
            success=True,
            code=200,
            data={},
            message='Product theme removed successfully.',
        )
        return Response(success_response, status=status.HTTP_200_OK)
