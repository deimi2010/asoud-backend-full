from rest_framework import views, status
from rest_framework.response import Response
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q, Count, Sum, Avg, F
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from drf_spectacular.types import OpenApiTypes

from utils.response import ApiResponse
from apps.core.api_optimization import OptimizedAPIView
from apps.core.performance import QueryProfiler
from apps.core.permissions import IsAuthenticatedUser
from apps.referral.access import viewable_markets

from apps.market.models import (
    Market,
    MarketBookmark,
)

from apps.market.serializers.user_serializers import (
    MarketBookmarkEnvelopeSerializer,
    MarketBookmarkListEnvelopeSerializer,
    MarketBookmarkUpdateSerializer,
    MarketListSerializer,
    MarketReportCreateSerializer,
)


@extend_schema(
    summary="Get User's Markets",
    description="Retrieve a paginated list of markets owned by the authenticated user with detailed statistics including products count, sales, revenue, and more.",
    parameters=[
        OpenApiParameter(
            name='page',
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            description='Page number for pagination',
            required=False,
            default=1
        ),
        OpenApiParameter(
            name='page_size',
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            description='Number of items per page',
            required=False,
            default=20
        ),
    ],
    responses={
        200: OpenApiResponse(response=MarketListSerializer(many=True)),
        401: OpenApiResponse(description='Authentication required'),
    },
    tags=['Markets - User']
)
class MarketListAPIView(OptimizedAPIView):
    permission_classes = [IsAuthenticatedUser]
    """
    Optimized market list view with performance enhancements.
    
    This view provides a list of markets owned by the authenticated user
    with advanced performance optimizations including query profiling,
    select_related, and prefetch_related for efficient database access.
    
    Attributes:
        permission_classes: IsAuthenticated - Requires authentication
    """
    
    def get(self, request, format=None):
        user_obj = self.request.user
        
        with QueryProfiler():
            # Get optimized queryset with select_related and prefetch_related
            market_list = Market.objects.filter(
                user=user_obj,
            ).select_related(
                'sub_category',
                'location',
                'contact'
            ).prefetch_related(
                'products',
                'viewed_by'
            ).annotate(
                products_count=Count('products'),
                published_products=Count('products', filter=Q(products__status='published')),
                total_sales=Sum(
                    'products__orderitem__quantity',
                    filter=Q(products__orderitem__order__is_paid=True)
                ),
                total_revenue=Sum(
                    F('products__orderitem__quantity') * F('products__main_price'),
                    filter=Q(products__orderitem__order__is_paid=True)
                ),
                average_product_price=Avg('products__main_price'),
                low_stock_products=Count('products', filter=Q(products__stock__lte=10))
            ).order_by('-created_at')

            # Apply pagination
            page_size = int(request.GET.get('page_size', 20))
            page_number = int(request.GET.get('page', 1))
            
            paginator = Paginator(market_list, page_size)
            page = paginator.get_page(page_number)

            serializer = MarketListSerializer(
                page.object_list,
                many=True,
                context={"request": request},
            )

            # Create optimized response
            response_data = {
                'results': serializer.data,
                'pagination': {
                    'count': paginator.count,
                    'total_pages': paginator.num_pages,
                    'current_page': page.number,
                    'has_next': page.has_next(),
                    'has_previous': page.has_previous(),
                    'next_page': page.next_page_number() if page.has_next() else None,
                    'previous_page': page.previous_page_number() if page.has_previous() else None,
                }
            }

            success_response = ApiResponse(
                success=True,
                code=200,
                data=response_data,
                message='Data retrieved successfully'
            )

            return Response(success_response)


class PublicMarketListAPIView(OptimizedAPIView):
    serializer_class = MarketListSerializer
    permission_classes = [IsAuthenticatedUser]
    """
    Optimized public market list view with caching and performance enhancements.
    
    This view provides a public list of published markets with advanced
    caching, filtering, and pagination capabilities for optimal performance.
    
    Attributes:
        permission_classes: [] - No authentication required (public access)
    """
    permission_classes = [IsAuthenticatedUser]
    
    def get(self, request, format=None):
        with QueryProfiler():
            # Get search and filter parameters
            search_term = request.GET.get('search', '').strip()
            category_id = request.GET.get('category', None)
            verified_only = request.GET.get('verified', 'false').lower() == 'true'
            
            # Build optimized queryset
            market_list = viewable_markets(request.user).filter(
                status=Market.PUBLISHED
            ).select_related(
                'sub_category',
                'location',
                'contact',
                'user'
            ).prefetch_related(
                'viewed_by',
                'products'
            ).annotate(
                products_count=Count('products'),
                published_products=Count('products', filter=Q(products__status='published')),
                average_product_price=Avg('products__main_price'),
                total_views=Count('viewed_by')
            ).order_by('-total_views', '-created_at')

            # Apply filters
            if verified_only:
                market_list = market_list.filter(is_verified=True)
            
            if category_id:
                market_list = market_list.filter(sub_category_id=category_id)
            
            if search_term:
                market_list = market_list.filter(
                    Q(name__icontains=search_term) |
                    Q(description__icontains=search_term) |
                    Q(business_id__icontains=search_term)
                )

            # Apply pagination (robust parsing)
            try:
                page_size = int(request.GET.get('page_size', 20))
            except (TypeError, ValueError):
                page_size = 20
            page_size = min(max(page_size, 1), 100)
            try:
                page_number = int(request.GET.get('page', 1))
            except (TypeError, ValueError):
                page_number = 1
            
            paginator = Paginator(market_list, page_size)
            page = paginator.get_page(page_number)

            serializer = MarketListSerializer(
                page.object_list,
                many=True,
                context={"request": request},
            )

            # Create optimized response
            response_data = {
                'results': serializer.data,
                'pagination': {
                    'count': paginator.count,
                    'total_pages': paginator.num_pages,
                    'current_page': page.number,
                    'has_next': page.has_next(),
                    'has_previous': page.has_previous(),
                    'next_page': page.next_page_number() if page.has_next() else None,
                    'previous_page': page.previous_page_number() if page.has_previous() else None,
                },
                'filters': {
                    'search_term': search_term,
                    'category_id': category_id,
                    'verified_only': verified_only,
                }
            }

            success_response = ApiResponse(
                success=True,
                code=200,
                data=response_data,
                message='Data retrieved successfully'
            )

            return Response(success_response)


class MarketReportAPIView(views.APIView):
    serializer_class = MarketReportCreateSerializer
    def post(self, request, pk):
        try:
            market = Market.objects.get(id=pk)
        except Market.DoesNotExist:
            return Response(
                ApiResponse(
                    success=False,
                    code=404,
                    error="Market Not Found"
                ),
                status=status.HTTP_404_NOT_FOUND,
            )
        
        user = self.request.user

        serializer = MarketReportCreateSerializer(
            data=request.data,
            context={'request': request},
        )

        if serializer.is_valid(raise_exception=True):
            serializer.save(
                market=market,
                creator=user,
            )

            success_response = ApiResponse(
                success=True,
                code=200,
                data={
                    **serializer.data,
                },
                message='Market report created successfully.',
            )

            return Response(success_response, status=status.HTTP_201_CREATED)

        response = ApiResponse(
            success=False,
            code=500,
            error={
                'code': 'server_error',
                'detail': 'Server error',
            }
        )

        return Response(response, status=status.HTTP_200_OK)


class MarketBookmarkListAPIView(views.APIView):
    @extend_schema(responses={200: MarketBookmarkListEnvelopeSerializer})
    def get(self, request):
        market_list = (
            Market.objects.filter(
                status=Market.PUBLISHED,
                bookmarked_by__user=request.user,
                bookmarked_by__is_active=True,
            )
            .select_related("sub_category")
            .prefetch_related("viewed_by")
            .order_by("-bookmarked_by__created_at")
        )

        serializer = MarketListSerializer(
            market_list,
            many=True,
            context={"request": request},
        )

        success_response = ApiResponse(
            success=True,
            code=200,
            data=serializer.data,
            message="Data retrieved successfully",
        )

        return Response(success_response)



class MarketBookmarkUpdateAPIView(views.APIView):
    @extend_schema(
        request=MarketBookmarkUpdateSerializer,
        responses={200: MarketBookmarkEnvelopeSerializer},
        description=(
            "Idempotently sets the authenticated user's bookmark state for a "
            "published market."
        ),
    )
    @transaction.atomic
    def put(self, request, pk):
        request_serializer = MarketBookmarkUpdateSerializer(data=request.data)
        request_serializer.is_valid(raise_exception=True)
        desired = request_serializer.validated_data["bookmarked"]

        market = (
            Market.objects.select_for_update()
            .filter(id=pk, status=Market.PUBLISHED)
            .first()
        )
        if market is None:
            return Response(
                ApiResponse(
                    success=False,
                    code=404,
                    error="Published market not found",
                ),
                status=status.HTTP_404_NOT_FOUND,
            )

        bookmark = (
            MarketBookmark.objects.select_for_update()
            .filter(user=request.user, market=market)
            .first()
        )
        if bookmark is None and desired:
            bookmark = MarketBookmark.objects.create(
                user=request.user,
                market=market,
                is_active=True,
            )
        elif bookmark is not None and bookmark.is_active != desired:
            bookmark.is_active = desired
            bookmark.save(update_fields=["is_active", "updated_at"])

        message = "Market bookmarked." if desired else "Market unbookmarked."
        return Response(
            ApiResponse(
                success=True,
                code=200,
                data={"market_id": str(market.id), "bookmarked": desired},
                message=message,
            ),
            status=status.HTTP_200_OK,
        )
