import logging

from rest_framework import views, status, permissions
from rest_framework.response import Response
from utils.response import ApiResponse
from django.db.models import Count, F, Q
from django.db import transaction
from apps.cart.models import (
    Order,
)
from apps.cart.serializers.owner import (
    OrderSerializer,
    OrderListSerializer,
    OrderVerifySerializer
)
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from apps.cart.services import (
    CartIntegrityError,
    confirm_order_inventory,
    release_order_inventory,
    reserve_order_inventory,
)


logger = logging.getLogger(__name__)


def _notify_order_status(user_id, order_id):
    try:
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"user_{user_id}",
            {
                "type": "send_notification",
                "data": {
                    "type": "order",
                    "message": "Order Status Updated By Owner",
                    "order": {"id": str(order_id)},
                },
            },
        )
    except Exception:
        logger.exception("Failed to publish order status update for order %s", order_id)


def _is_exclusively_owned_order(order, user):
    item_markets = set()
    for product_id, affiliate_id, product_market_id, affiliate_market_id in (
        order.items.values_list(
            'product_id',
            'affiliate_id',
            'product__market_id',
            'affiliate__market_id',
        )
    ):
        if (product_id is None) == (affiliate_id is None):
            return False
        item_markets.add(product_market_id or affiliate_market_id)
    owner_markets = set(user.markets.values_list('id', flat=True))
    return bool(item_markets) and item_markets.issubset(owner_markets)


class OrderVerifyView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    @transaction.atomic
    def put(self, request):
        serializer = OrderVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            order = Order.objects.select_for_update().get(
                id=serializer.validated_data['id']
            )
        except Order.DoesNotExist:
            return Response(
                ApiResponse(
                    success=False,
                    code=404,
                    error={
                        'code': 'order_not_found',
                        'detail': 'Order not found',
                    }
                ),
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Ownership check - verify the order contains items from user's market
        if not _is_exclusively_owned_order(order, request.user):
            return Response(
                ApiResponse(
                    success=False,
                    code=403,
                    error={
                        'code': 'permission_denied',
                        'detail': 'You do not have permission to verify this order',
                    }
                ),
                status=status.HTTP_403_FORBIDDEN,
            )
        
        if order.status != Order.PENDING:
            return Response(
                ApiResponse(
                    success=False,
                    code=400,
                    error={
                        'code': 'invalid_status',
                        'detail': 'Order is not in pending status',
                    }
                ),
                status=status.HTTP_400_BAD_REQUEST
            )

        if not serializer.validated_data['verified']:
            release_order_inventory(order)
            order.status = Order.REJECTED
        elif order.type == Order.CASH:
            try:
                reserve_order_inventory(order)
                confirm_order_inventory(order)
            except CartIntegrityError as exc:
                return Response(
                    ApiResponse(success=False, code=400, error={'code': exc.code, 'detail': exc.detail}),
                    status=status.HTTP_400_BAD_REQUEST,
                )
            order.status = Order.COMPLETED
            order.is_paid = True
        else:
            order.status = Order.VERIFIED
        
        order.owner_description = serializer.validated_data['description']
        order.save()

        transaction.on_commit(
            lambda: _notify_order_status(order.user_id, order.id)
        )

        serializer = OrderSerializer(order)

        return Response(
            ApiResponse(
                success=True,
                code=200,
                data=serializer.data
            ),
            status=status.HTTP_200_OK
        )
        

class OrderListView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        owner_filter = Q(items__product__market__user=request.user) | Q(
            items__affiliate__market__user=request.user
        )
        market_owner_orders = Order.objects.exclude(status=Order.DRAFT).annotate(
            item_count=Count('items', distinct=True),
            owner_item_count=Count('items', filter=owner_filter, distinct=True),
            invalid_item_count=Count(
                'items',
                filter=(
                    Q(items__product__isnull=True, items__affiliate__isnull=True)
                    | Q(items__product__isnull=False, items__affiliate__isnull=False)
                ),
                distinct=True,
            ),
        ).filter(
            item_count__gt=0,
            item_count=F('owner_item_count'),
            invalid_item_count=0,
        ).select_related(
            'user'
        ).prefetch_related(
            'items__product__market',
            'items__affiliate__market'
        ).distinct()

        serializer = OrderListSerializer(market_owner_orders, many=True)

        return Response(
            ApiResponse(
                success=True,
                code=200,
                data=serializer.data
            ),
            status=status.HTTP_200_OK
        )
    
class OrderDetailView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, pk:str):
        try:
            order = Order.objects.get(id=pk)
        except Order.DoesNotExist:
            return Response(
                ApiResponse(
                    success=False,
                    code=404,
                    error={
                        'code': 'order_not_found',
                        'detail': 'Order not found',
                    }
                ),
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Ownership check - verify the order contains items from user's market
        if not _is_exclusively_owned_order(order, request.user):
            return Response(
                ApiResponse(
                    success=False,
                    code=403,
                    error={
                        'code': 'permission_denied',
                        'detail': 'You do not have permission to view this order',
                    }
                ),
                status=status.HTTP_403_FORBIDDEN,
            )
            
        serializer = OrderSerializer(order)
        return Response(
            ApiResponse(
                success=True,
                code=200,
                data=serializer.data
            ),
            status=status.HTTP_200_OK
        )
