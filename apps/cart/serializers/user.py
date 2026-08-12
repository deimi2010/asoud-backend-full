from rest_framework import serializers
from apps.cart.models import (
    Order, 
    OrderItem
)
from apps.product.models import Product, ProductImage
from apps.affiliate.models import AffiliateProduct, AffiliateProductImage
from django.db import transaction
from apps.cart.services import snapshot_order


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ('id', 'image')


class ProductSimpleSerializer(serializers.ModelSerializer):
    images = ProductImageSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = ('id', 'name', 'images')


class AffiliateImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = AffiliateProductImage
        fields = ('id', 'image')


class AffiliateSimpleSerializer(serializers.ModelSerializer):
    images = AffiliateImageSerializer(many=True, read_only=True)

    class Meta:
        model = AffiliateProduct
        fields = ('id', 'name', 'images')

class OrderItem2Serializer(serializers.ModelSerializer):
    product = ProductSimpleSerializer(read_only=True)
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(),
        source='product',  # Maps to the 'product' FK field
        write_only=True,    # Only used for input, not output
        required=False,
        allow_null=True
    )
    affiliate = AffiliateSimpleSerializer(read_only=True)
    affiliate_id = serializers.PrimaryKeyRelatedField(
        queryset=AffiliateProduct.objects.all(),
        source='affiliate',
        write_only=True,
        required=False,  # Since affiliate is optional
        allow_null=True  # Allows null in POST data
    )
    class Meta:
        model = OrderItem
        fields = (
            'id',
            'product',
            'product_id',
            'affiliate',
            'affiliate_id',
            'quantity',
        )

    def validate_quantity(self, value):
        if value < 1:
            raise serializers.ValidationError('Quantity must be at least 1.')
        return value

    def validate(self, attrs):
        if bool(attrs.get('product')) == bool(attrs.get('affiliate')):
            raise serializers.ValidationError(
                'Provide exactly one of product_id or affiliate_id.'
            )
        return attrs


class OrderItemUpdateSerializer(serializers.ModelSerializer):
    # Keep these read-only for display purposes
    item = serializers.SerializerMethodField(read_only=True)
    item_type = serializers.SerializerMethodField(read_only=True)
    total_price = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = OrderItem
        fields = ['id', 'quantity', 'item', 'item_type', 'total_price']
    
    def get_item(self, obj):
        if obj.product:
            return Product1Serializer(obj.product).data
        elif obj.affiliate:
            return AffiliateProduct1Serializer(obj.affiliate).data
        return None
    
    def get_item_type(self, obj):
        if obj.product:
            return 'product'
        elif obj.affiliate:
            return 'affiliate'
        return None
    
    def get_total_price(self, obj):
        return obj.total_price()
    
    def validate_quantity(self, value):
        if value < 1:
            raise serializers.ValidationError("Quantity must be at least 1")
        return value
    # price = serializers.SerializerMethodField()
    # total_price = serializers.SerializerMethodField()
    # def get_price(self, obj):
    #     if obj.product:
    #         print("PRICE", obj.product.price)
    #         return obj.product.price
    #     elif obj.affiliate:
    #         print("PRICE1", obj.product.price)
    #         return obj.affiliate.price
    #     return 0
    
    # def get_total_price(self, obj):
    #     print("total_price", obj.product.price)
    #     return obj.total_price()
    
    # def get_product(self, obj):
        
    # def get_product(self, obj):
    #     print("###", obj)
    #     if obj.product:
    #         return obj.product.name
    #     elif obj.affiliate:
    #         return obj.affiliate.name
    #     return "unknown"

class Product1Serializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ['id', 'name']  

class AffiliateProduct1Serializer(serializers.ModelSerializer):
    class Meta:
        model = AffiliateProduct
        fields = ['id', 'name']


class OrderItem1Serializer(serializers.ModelSerializer):
    item = serializers.SerializerMethodField()
    item_type = serializers.SerializerMethodField()
    total_price = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = ['id', 'quantity', 'total_price', 'item', 'item_type']
    
    def get_item(self, obj):
        if obj.product:
            return Product1Serializer(obj.product).data
        elif obj.affiliate:
            return AffiliateProduct1Serializer(obj.affiliate).data
        return None
    
    def get_item_type(self, obj):
        if obj.product:
            return 'product'
        elif obj.affiliate:
            return 'affiliate'
        return None
    
    def get_total_price(self, obj):
        return obj.total_price()
    

class Order2Serializer(serializers.ModelSerializer):
    items = OrderItem1Serializer(many=True, read_only=True)
    total_price = serializers.SerializerMethodField()
    total_items = serializers.SerializerMethodField()
    
    class Meta:
        model = Order
        fields = ['id', 'items', 'total_price', 'total_items', 'created_at', 'updated_at']
    
    def get_total_price(self, obj):
        return obj.total_price()
    
    def get_total_items(self, obj):
        return obj.total_items()
    

class OrderCheckOutSerializer(serializers.ModelSerializer):
    discount_code = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=16,
        write_only=True,
    )

    class Meta:
        model = Order
        fields = [
            'description', 
            'type',
            'discount_code',
        ]

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

class OrderItemCreateSerializer(serializers.ModelSerializer):
    product_id = serializers.PrimaryKeyRelatedField(
        source='product',
        queryset=Product.objects.all(),
        required=False,
    )
    affiliate_id = serializers.PrimaryKeyRelatedField(
        source='affiliate',
        queryset=AffiliateProduct.objects.all(),
        required=False,
    )
    class Meta:
        model = OrderItem
        fields = [
            'product_id', 
            'affiliate_id',
            'quantity'
        ]

    def validate(self, attrs):
        if bool(attrs.get('product')) == bool(attrs.get('affiliate')):
            raise serializers.ValidationError(
                'Provide exactly one of product_id or affiliate_id.'
            )
        return attrs


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
            'type',
            'status',
            'owner_description',
            'subtotal_amount',
            'discount_amount',
            'discount_code_snapshot',
            'inventory_status',
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
    
class OrderCreateSerializer(serializers.ModelSerializer):
    items = OrderItemCreateSerializer(many=True)
    description = serializers.CharField(required=False)
    type = serializers.ChoiceField(choices=['online', 'cash'])

    class Meta:
        model = Order
        fields = [
            'description', 
            'type',
            'items'
        ]

    @transaction.atomic
    def create(self, validated_data):
        items_data = validated_data.pop('items')
        order = Order.objects.create(status=Order.DRAFT, **validated_data)
        for item_data in items_data:
            OrderItem.objects.create(
                order=order, 
                product=item_data.get('product'),
                affiliate=item_data.get('affiliate'),
                quantity=item_data['quantity'], 
            )
        snapshot_order(order)
        order.status = Order.PENDING
        order.save(update_fields=['status', 'updated_at'])
        return order
    

    def update(self, instance, validated_data):
        items_data = validated_data.pop('items', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        with transaction.atomic():
            # If new items are provided, replace the old ones
            if items_data is not None:
                # Delete existing items
                instance.items.all().delete()

                # Add new items
                for item_data in items_data:
                    product = item_data.get('product')
                    affiliate = item_data.get('affiliate')
                    quantity = item_data.get('quantity')

                    # Create the OrderItem
                    OrderItem.objects.create(
                        order=instance,
                        product=product,
                        affiliate=affiliate,
                        quantity=quantity
                    )

        # Save the updated Order instance
        instance.save()

        if instance.status == Order.DRAFT:
            from apps.cart.services import clear_order_snapshot

            clear_order_snapshot(instance)

        return instance
    
