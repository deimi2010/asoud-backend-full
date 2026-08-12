from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field

from apps.market.models import Market
from apps.product.models import Product
from apps.product.serializers.owner_serializers import (
    ProductDetailSerializer,
    ProductListSerializer,
)


class PublicProductDetailSerializer(ProductDetailSerializer):
    """Customer-safe product details without owner pricing or workflow fields."""

    required_product = serializers.SerializerMethodField()
    gift_product = serializers.SerializerMethodField()

    class Meta(ProductDetailSerializer.Meta):
        fields = [
            'id',
            'name',
            'description',
            'technical_detail',
            'keywords',
            'stock',
            'main_price',
            'required_product',
            'gift_product',
            'tag',
            'tag_position',
            'sell_type',
            'ship_cost_pay_type',
            'shipping_cost',
            'images',
        ]

    def _public_related(self, product):
        if (
            product is None
            or product.status != Product.PUBLISHED
            or product.market.status != Market.PUBLISHED
        ):
            return None
        return ProductListSerializer(product, context=self.context).data

    @extend_schema_field(ProductListSerializer(allow_null=True))
    def get_required_product(self, obj):
        return self._public_related(obj.required_product)

    @extend_schema_field(ProductListSerializer(allow_null=True))
    def get_gift_product(self, obj):
        return self._public_related(obj.gift_product)


class ProductDetailQuerySerializer(serializers.Serializer):
    id = serializers.UUIDField()


class PublicProductDetailEnvelopeSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    code = serializers.IntegerField()
    data = PublicProductDetailSerializer()
