import logging

from rest_framework import views, viewsets, status, permissions
from rest_framework.response import Response
from drf_spectacular.utils import OpenApiResponse, extend_schema
from utils.response import ApiResponse
from apps.cart.models import (
    Order,
    OrderItem
)
from apps.cart.serializers.user import(
    OrderSerializer,
    Order2Serializer,
    OrderItem2Serializer,
    OrderCreateSerializer,
    OrderCheckOutSerializer,
    OrderItemUpdateSerializer
)
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import IntegrityError, transaction
from apps.users.models import User
from apps.affiliate.models import AffiliateProduct
from apps.product.models import Product
from apps.cart.services import (
    CartIntegrityError,
    clear_order_snapshot,
    snapshot_order,
    validate_catalog_target,
)
from apps.analytics.models import AnalyticsEvent
from apps.analytics.services import AnalyticsRecorder


logger = logging.getLogger(__name__)


def _notify_market_owner(user_id, order_id, message):
    try:
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"user_{user_id}",
            {
                "type": "send_notification",
                "data": {
                    "type": "order",
                    "message": message,
                    "order": {"id": str(order_id)},
                },
            },
        )
    except Exception:
        logger.exception("Failed to publish order update for order %s", order_id)


def _lock_catalog_target(*, product_id=None, affiliate_id=None):
    if product_id:
        return Product.objects.select_for_update().select_related('market').get(id=product_id)
    affiliate_ref = AffiliateProduct.objects.only('product_id').get(id=affiliate_id)
    source = (
        Product.objects.select_for_update()
        .select_related('market')
        .get(id=affiliate_ref.product_id)
    )
    affiliate = (
        AffiliateProduct.objects.select_for_update()
        .select_related('market')
        .get(id=affiliate_id)
    )
    affiliate.product = source
    return affiliate


@extend_schema(
    summary="Cart Operations",
    description="Manage user's shopping cart including adding items, updating quantities, and viewing cart contents.",
    tags=['Cart & Orders - User']
)
class CartViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]
    
    def get_order(self, request, lock=False):
        """Helper method to get or create order"""
        orders = Order.objects
        if lock:
            # The user row is the per-cart mutex, including the no-cart-yet case.
            User.objects.select_for_update().get(id=request.user.id)
            orders = orders.select_for_update()
        order, _ = orders.get_or_create(
            user=request.user,
            status=Order.DRAFT,
            defaults={
                'type': Order.ONLINE,
                'description': 'Shopping order',
            },
        )
        return order
    
    @transaction.atomic
    def list(self, request):
        """Get order contents"""
        order = self.get_order(request, lock=True)
        serializer = Order2Serializer(order)
        return Response(serializer.data)
    
    @transaction.atomic
    def add_item(self, request):
        """Add item to cart"""
        order = self.get_order(request, lock=True)
        serializer = OrderItem2Serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        product = serializer.validated_data.get('product')
        affiliate = serializer.validated_data.get('affiliate')
        quantity = serializer.validated_data['quantity']
        if product:
            target = _lock_catalog_target(product_id=product.id)
            existing = order.items.select_for_update().filter(product=target).first()
        else:
            target = _lock_catalog_target(affiliate_id=affiliate.id)
            existing = order.items.select_for_update().filter(affiliate=target).first()

        try:
            validate_catalog_target(target)
        except CartIntegrityError as exc:
            return Response(
                {'error': {'code': exc.code, 'detail': exc.detail}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        existing_market_id = (
            order.items.exclude(id=getattr(existing, 'id', None))
            .values_list('product__market_id', 'affiliate__market_id')
            .first()
        )
        if existing_market_id:
            market_id = existing_market_id[0] or existing_market_id[1]
            if market_id != target.market_id:
                return Response(
                    {'error': 'All cart items must belong to one market'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        new_quantity = quantity + (existing.quantity if existing else 0)
        if new_quantity > target.stock:
            return Response(
                {'error': f'Insufficient stock. Available: {target.stock}'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if existing:
            existing.quantity = new_quantity
            existing.save(update_fields=['quantity', 'updated_at'])
            item = existing
        else:
            item = OrderItem.objects.create(
                order=order,
                product=target if product else None,
                affiliate=target if affiliate else None,
                quantity=quantity,
            )
        canonical_product = target.product if affiliate else target
        AnalyticsRecorder.record_request(
            request,
            AnalyticsEvent.ADD_TO_CART,
            product=canonical_product,
            market=target.market,
            metadata={'quantity': quantity},
        )
        clear_order_snapshot(order)
        return Response(OrderItem2Serializer(item).data, status=status.HTTP_201_CREATED)
           
    @transaction.atomic
    def update_item(self, request, pk=None):
        """Update item quantity in cart"""
        order = self.get_order(request, lock=True)
        try:
            item = order.items.get(pk=pk)
        except OrderItem.DoesNotExist:
            return Response(
                {"error": "Item not found in order"}, 
                status=status.HTTP_404_NOT_FOUND
            )
    
        serializer = OrderItemUpdateSerializer(
            item, 
            data=request.data, 
            partial=True,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        target = _lock_catalog_target(
            product_id=item.product_id,
            affiliate_id=item.affiliate_id,
        )
        try:
            validate_catalog_target(target)
        except CartIntegrityError as exc:
            return Response(
                {'error': {'code': exc.code, 'detail': exc.detail}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if serializer.validated_data.get('quantity', item.quantity) > target.stock:
            return Response(
                {'error': f'Insufficient stock. Available: {target.stock}'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer.save()  # No need to pass order since it's already set
        clear_order_snapshot(order)
    
        return Response(serializer.data)
    
    @transaction.atomic
    def remove_item(self, request, pk=None):
        """Remove item from order"""
        order = self.get_order(request, lock=True)
        try:
            item = order.items.get(pk=pk)
            item.delete()
            clear_order_snapshot(order)
            serializer = Order2Serializer(order)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except OrderItem.DoesNotExist:
            return Response(
                {"error": "Item not found in order"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
    @transaction.atomic
    def checkout(self, request):
        order = self.get_order(request, lock=True)
        serializer = OrderCheckOutSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        
        try:
            with transaction.atomic():
                order.description = serializer.validated_data.get('description', 'Order placed')
                order.type = serializer.validated_data.get('type', Order.ONLINE)
                order.save(update_fields=['description', 'type', 'updated_at'])
                snapshot_order(order, serializer.validated_data.get('discount_code', ''))
                order.status = Order.PENDING
                order.save(update_fields=['status', 'updated_at'])
        except CartIntegrityError as exc:
            return Response(
                {'error': {'code': exc.code, 'detail': exc.detail}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = Order2Serializer(order)
        return Response(
            {"message": "Order placed successfully", "order": serializer.data},
            status=status.HTTP_200_OK
        )

class OrderCreateView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        serializer = OrderCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            obj = serializer.save(user=request.user)
        except CartIntegrityError as exc:
            return Response(
                ApiResponse(success=False, code=400, error={'code': exc.code, 'detail': exc.detail}),
                status=status.HTTP_400_BAD_REQUEST,
            )
        except IntegrityError:
            return Response(
                ApiResponse(
                    success=False,
                    code=409,
                    error='An active draft cart already exists; use the checkout endpoint.',
                ),
                status=status.HTTP_409_CONFLICT,
            )
        
        if obj.items.first().product:
            user_id = obj.items.first().product.market.user.id
        else:
            user_id = obj.items.first().affiliate.market.user.id

        transaction.on_commit(
            lambda: _notify_market_owner(user_id, obj.id, "New Order Added")
        )

        serialized_data = OrderSerializer(obj).data

        return Response(
            ApiResponse(
                success=True,
                code=201,
                data=serialized_data
            ),
            status=status.HTTP_201_CREATED,
        )

@extend_schema(
    summary="Get User Orders",
    description="Retrieve all orders for the authenticated user with detailed order items.",
    responses={200: OpenApiResponse(response=OrderSerializer(many=True))},
    tags=['Cart & Orders - User']
)
class OrderListView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        orders = Order.objects.filter(
            user=request.user
        ).exclude(
            status=Order.DRAFT
        ).select_related(
            'user'
        ).prefetch_related(
            'items__product',
            'items__affiliate'
        )

        serializer = OrderSerializer(orders, many=True)
        return Response(
            ApiResponse(
                success=True,
                code=200,
                data=serializer.data
            )
        )

class OrderDetailView(views.APIView):
    """
    Get order details with ownership verification
    
    Security: Only owner can view their orders
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, pk:str):
        try:
            # ✅ FIXED: Add ownership check
            order = Order.objects.select_related('user').get(
                id=pk,
                user=request.user  # Ownership check!
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
        
        except Order.DoesNotExist:
            # ✅ FIXED: Proper exception handling
            return Response(
                ApiResponse(
                    success=False,
                    code=404,
                    error="Order not found"  # Generic message
                ),
                status=status.HTTP_404_NOT_FOUND
            )
        
        except Exception as e:
            # ✅ FIXED: Log but don't expose details
            logger.error(f"Error in OrderDetailView: {str(e)}", exc_info=True)
            return Response(
                ApiResponse(
                    success=False,
                    code=500,
                    error="An internal error occurred"  # Generic message
                ),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class OrderUpdateView(views.APIView):
    """
    Update order with ownership verification
    
    Security: Only owner can update their own orders
    """
    permission_classes = [permissions.IsAuthenticated]
    
    @transaction.atomic
    def put(self, request, pk:str):
        try:
            User.objects.select_for_update().get(id=request.user.id)
            # ✅ FIXED: Add ownership check and select_related
            order = Order.objects.select_for_update().select_related('user').prefetch_related('items').get(
                id=pk,
                user=request.user  # Ownership check!
            )
            
            # ✅ Check if order is editable
            if order.status != Order.DRAFT:
                return Response(
                    ApiResponse(
                        success=False,
                        code=400,
                        error="Order cannot be modified in current status"
                    ),
                    status=status.HTTP_400_BAD_REQUEST
                )

            serializer = OrderCreateSerializer(order, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)

            # ✅ FIXED: Don't override user
            obj = serializer.save()

            # ✅ FIXED: Safe navigation with proper checks
            try:
                first_item = obj.items.first()
                if first_item:
                    if first_item.product and first_item.product.market:
                        market_owner_id = first_item.product.market.user.id
                    elif first_item.affiliate and first_item.affiliate.market:
                        market_owner_id = first_item.affiliate.market.user.id
                    else:
                        market_owner_id = None
                    
                    if market_owner_id:
                        transaction.on_commit(
                            lambda: _notify_market_owner(
                                market_owner_id,
                                obj.id,
                                "An Order Updated",
                            )
                        )
            except Exception as notif_error:
                # ✅ Don't fail if notification fails
                logger.warning(f"Failed to send notification: {notif_error}")

            serialized_data = OrderSerializer(obj).data

            return Response(
                ApiResponse(
                    success=True,
                    code=200,
                    data=serialized_data
                ),
                status=status.HTTP_200_OK
            )
        
        except Order.DoesNotExist:
            return Response(
                ApiResponse(
                    success=False,
                    code=404,
                    error="Order not found"
                ),
                status=status.HTTP_404_NOT_FOUND
            )
        
        except Exception as e:
            logger.error(f"Error in OrderUpdateView: {str(e)}", exc_info=True)
            return Response(
                ApiResponse(
                    success=False,
                    code=500,
                    error="An internal error occurred"
                ),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class OrderDeleteView(views.APIView):
    """
    Delete order with ownership verification
    
    Security: Only owner can delete their own draft orders
    """
    permission_classes = [permissions.IsAuthenticated]
    
    @transaction.atomic
    def delete(self, request, pk:str):
        try:
            User.objects.select_for_update().get(id=request.user.id)
            # ✅ FIXED: Add ownership check
            order = Order.objects.select_for_update().get(
                id=pk,
                user=request.user  # Ownership check!
            )
            
            # ✅ Business rule: Only draft orders can be deleted
            if order.status != Order.DRAFT:
                return Response(
                    ApiResponse(
                        success=False,
                        code=400,
                        error="Only draft orders can be deleted"
                    ),
                    status=status.HTTP_400_BAD_REQUEST
                )

            order.delete()
        
            return Response(
                ApiResponse(
                    success=True,
                    code=204,
                    message="Order deleted successfully"
                ),
                status=status.HTTP_204_NO_CONTENT
            )
        
        except Order.DoesNotExist:
            return Response(
                ApiResponse(
                    success=False,
                    code=404,
                    error="Order not found"
                ),
                status=status.HTTP_404_NOT_FOUND
            )
        
        except Exception as e:
            logger.error(f"Error in OrderDeleteView: {str(e)}", exc_info=True)
            return Response(
                ApiResponse(
                    success=False,
                    code=500,
                    error="An internal error occurred"
                ),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
