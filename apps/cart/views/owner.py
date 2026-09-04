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
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from apps.market.access import accessible_markets
from apps.affiliate.services import accrue_order_commissions, reverse_order_commissions


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
    for product_id, affiliate_id, product_market_id, affiliate_source_market_id in (
        order.items.values_list(
            'product_id',
            'affiliate_id',
            'product__market_id',
            'affiliate__product__market_id',
        )
    ):
        if (product_id is None) == (affiliate_id is None):
            return False
        item_markets.add(product_market_id or affiliate_source_market_id)
    owner_markets = set(
        accessible_markets(user, write=True).values_list('id', flat=True)
    )
    return bool(item_markets) and item_markets.issubset(owner_markets)


class OrderVerifyView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    @extend_schema(request=OrderVerifySerializer, responses={200: OrderSerializer}, tags=['Cart & Orders - Owner'])
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
            accrue_order_commissions(order)
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
    
    @extend_schema(responses={200: OrderListSerializer(many=True)}, tags=['Cart & Orders - Owner'])
    def get(self, request):
        managed_markets = accessible_markets(request.user, write=True)
        owner_filter = Q(items__product__market__in=managed_markets) | Q(
            items__affiliate__product__market__in=managed_markets
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
            'items__affiliate__market',
            'items__affiliate__product__market',
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


class OrderFulfillmentView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        request=inline_serializer(
            name='OrderFulfillmentRequest',
            fields={'status': serializers.ChoiceField(choices=(Order.PREPARING, Order.SHIPPED, Order.RETURNED))},
        ),
        responses={200: OrderSerializer},
        tags=['Cart & Orders - Owner'],
    )
    @transaction.atomic
    def put(self, request, pk):
        try:
            order = Order.objects.select_for_update().get(id=pk, is_paid=True)
        except Order.DoesNotExist:
            return Response({'detail': 'Paid order not found'}, status=404)
        if not _is_exclusively_owned_order(order, request.user):
            return Response({'detail': 'Permission denied'}, status=403)
        desired = request.data.get('status')
        allowed = {
            Order.UNFULFILLED: {Order.PREPARING},
            Order.PREPARING: {Order.SHIPPED},
            Order.SHIPPED: {Order.RETURNED},
            Order.DELIVERED: {Order.RETURNED},
        }
        if desired not in allowed.get(order.fulfillment_status, set()):
            return Response({'detail': 'Invalid fulfillment transition'}, status=400)
        order.fulfillment_status = desired
        order.save(update_fields=('fulfillment_status', 'updated_at'))
        if desired == Order.RETURNED:
            reverse_order_commissions(order, 'Order returned')
        transaction.on_commit(lambda: _notify_order_status(order.user_id, order.id))
        return Response(OrderSerializer(order).data)
    
class OrderDetailView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    @extend_schema(responses={200: OrderSerializer}, tags=['Cart & Orders - Owner'])
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
