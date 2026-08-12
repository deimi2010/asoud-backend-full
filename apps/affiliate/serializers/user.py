from rest_framework import serializers
from apps.affiliate.models import (
    AffiliateProduct,
    AffiliateProductTheme,
    AffiliateProductImage
)
from apps.product.serializers.owner_serializers import ProductListSerializer

class AffiliateProductImageSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(read_only=True)

    class Meta:
        model = AffiliateProductImage
        fields = [
            'id',
            'image'
        ]

class AffiliateProductCreateSerializer(serializers.ModelSerializer):
    images = serializers.ListField(child=serializers.ImageField(), required=False)

    class Meta:
        model = AffiliateProduct
        fields = [
            'market',
            'product',
            'sub_category',
            'name',
            'description',
            'technical_detail',
            'stock',
            'price',
            'status',
            'required_product',
            'gift_product',
            'is_requirement',
            'tag',
            'tag_position',
            'sell_type',
            'ship_cost',
            'ship_cost_pay_type',
            'images'
        ]
        read_only_fields = ['status']

    def create(self, validated_data):
        # remove images 
        images = validated_data.pop('images', None)

        keywords_data = validated_data.pop('keywords', [])
        product = AffiliateProduct.objects.create(**validated_data)

        product.keywords.set(keywords_data)
        
        if images:
            for image in images:
                _ = AffiliateProductImage.objects.create(
                    product=product,
                    image=image
                )

        return product

    def update(self, instance, validated_data):
        # remove images 
        images = validated_data.pop('images', None)

        keywords_data = validated_data.pop('keywords', [])

        
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        # add keywords
        if keywords_data:
            instance.keywords.set(keywords_data)


        # add images
        if images:
            for image in instance.images.all():
                image.delete()

            for image in images:
                _ = AffiliateProductImage.objects.create(
                    product = instance,
                    image=image
                )

        instance.save()
        return instance
    
class AffiliateProductListSerializer(serializers.ModelSerializer):
    images = AffiliateProductImageSerializer(many=True)

    class Meta:
        model = AffiliateProduct
        fields = [
            'id',
            'name',
            'description',
            'price',
            'images',
        ]

class AffiliateProductDetailSerializer(serializers.ModelSerializer):
    product = ProductListSerializer(read_only=True)
    required_product = ProductListSerializer(read_only=True)
    gift_product = ProductListSerializer(read_only=True)
    images = AffiliateProductImageSerializer(many=True)

    class Meta:
        model = AffiliateProduct
        fields = [
            'id',
            'name',
            'product',
            'sub_category',
            'description',
            'technical_detail',
            'stock',
            'price',
            'required_product',
            'gift_product',
            'status',
            'is_requirement',
            'tag',
            'tag_position',
            'sell_type',
            'ship_cost',
            'ship_cost_pay_type',
            'theme',
            'images',
        ]

class AffiliateProductThemeCreateSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(read_only=True)

    class Meta:
        model = AffiliateProductTheme
        fields = [
            'id',
            'name',
            'order',
        ]

class AffiliateProductThemeListSerializer(serializers.ModelSerializer):
    affiliate_products = AffiliateProductListSerializer(many=True)

    class Meta:
        model = AffiliateProductTheme
        fields = [
            'id',
            'name',
            'order',
            'affiliate_products',
        ]

