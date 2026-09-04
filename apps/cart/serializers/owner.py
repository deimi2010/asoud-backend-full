from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from apps.cart.models import (
    Order,
    OrderItem
)
class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.SerializerMethodField()
    class Meta:
        model = OrderItem
        ref_name = 'OwnerOrderItem'
        fields = [
            'product_name', 
            'quantity'
        ]

    @extend_schema_field(serializers.CharField)
    def get_product_name(self, obj):
        if obj.product:
            return obj.product.name
        elif obj.affiliate:
            return obj.affiliate.name
        return "unknown"
    

class OrderListSerializer(serializers.ModelSerializer):
    total = serializers.SerializerMethodField()
    class Meta:
        model = Order
        fields = [
            'id',
            'description', 
            'created_at', 
            'is_paid',
            'total',
            'status',
            'fulfillment_status',
        ]

    @extend_schema_field(serializers.DecimalField(max_digits=14, decimal_places=3))
    def get_total(self, obj):
        return obj.total_price()


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True)
    total = serializers.SerializerMethodField()

    class Meta:
        model = Order
        ref_name = 'OwnerOrder'
        fields = [
            'id', 
            'description', 
            'created_at', 
            'is_paid',
            'total',
            'status',
            'owner_description',
            'subtotal_amount',
            'discount_amount',
            'shipping_method_name_snapshot',
            'shipping_amount',
            'payable_amount',
            'fulfillment_status',
            'delivered_at',
            'items'
        ]
        read_only_fields = [
            'id', 
            'user', 
            'created_at', 
            'is_paid'
        ]

    @extend_schema_field(serializers.DecimalField(max_digits=14, decimal_places=3))
    def get_total(self, obj):
        return obj.total_price()
    
class OrderVerifySerializer(serializers.Serializer):
    id = serializers.UUIDField()
    verified = serializers.BooleanField()
    description = serializers.CharField()
