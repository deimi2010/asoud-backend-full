from rest_framework import serializers
from apps.cart.models import (
    Order,
    OrderItem
)
from apps.product.models import Product
from apps.affiliate.models import AffiliateProduct


class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.SerializerMethodField()
    class Meta:
        model = OrderItem
        fields = [
            'product_name', 
            'quantity'
        ]

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
            'total'
        ]

    def get_total(self, obj):
        return obj.total_price()


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True)
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
            'owner_description',
            'items'
        ]
        read_only_fields = [
            'id', 
            'user', 
            'created_at', 
            'is_paid'
        ]

    def get_total(self, obj):
        return obj.total_price()
    
class OrderVerifySerializer(serializers.Serializer):
    id = serializers.UUIDField()
    verified = serializers.BooleanField()
    description = serializers.CharField()