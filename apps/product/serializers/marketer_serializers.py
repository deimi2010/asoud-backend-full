from rest_framework import serializers

from apps.product.models import Product


class ProductCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = [
            'market',
            'name',
            'description',
            'technical_detail',
            'stock',
            'price',
            'status',
            'required_product',
            'gift_product',
            'is_marketer',
            'marketer_price',
            'sell_type',
            'ship_cost',
            'ship_cost_pay_type',
        ]


class ProductListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = [
            'id',
            'name',
            'description',
            'price',
        ]
