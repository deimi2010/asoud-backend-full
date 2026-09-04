from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from apps.affiliate.models import (
    AffiliateProduct,
    AffiliateProductTheme,
    AffiliateProductImage
)
from apps.product.models import Product


class AffiliateBankProductSerializer(serializers.ModelSerializer):
    market_name = serializers.CharField(source='market.name', read_only=True)
    images = serializers.SerializerMethodField()
    minimum_profit = serializers.SerializerMethodField()
    maximum_profit = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = (
            'id', 'name', 'description', 'technical_detail', 'type',
            'sub_category', 'stock', 'main_price', 'marketer_price',
            'maximum_sell_price', 'sell_type', 'ship_cost_pay_type',
            'market_name', 'images', 'minimum_profit', 'maximum_profit',
        )

    @extend_schema_field(serializers.ListField(child=serializers.URLField()))
    def get_images(self, obj):
        request = self.context.get('request')
        values = []
        for row in obj.images.all():
            url = row.image.url
            values.append(request.build_absolute_uri(url) if request else url)
        return values

    @extend_schema_field(serializers.DecimalField(max_digits=14, decimal_places=3))
    def get_minimum_profit(self, obj):
        return '0.000'

    @extend_schema_field(serializers.DecimalField(max_digits=14, decimal_places=3, allow_null=True))
    def get_maximum_profit(self, obj):
        if obj.marketer_price is None or obj.maximum_sell_price is None:
            return None
        return str(obj.maximum_sell_price - obj.marketer_price)

class AffiliateProductImageSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(read_only=True)

    class Meta:
        model = AffiliateProductImage
        fields = [
            'id',
            'image'
        ]

class AffiliateProductCreateSerializer(serializers.ModelSerializer):
    images = serializers.ListField(
        child=serializers.ImageField(), required=False, max_length=6,
    )

    class Meta:
        model = AffiliateProduct
        fields = [
            'market',
            'product',
            'name',
            'description',
            'price',
            'status',
            'tag',
            'tag_position',
            'theme',
            'images'
        ]
        read_only_fields = ['status']
        validators = []

    def validate(self, attrs):
        attrs = super().validate(attrs)
        source = attrs.get('product') or getattr(self.instance, 'product', None)
        price = attrs.get('price', getattr(self.instance, 'price', None))
        market = attrs.get('market') or getattr(self.instance, 'market', None)
        theme = attrs.get('theme', getattr(self.instance, 'theme', None))
        if source is not None and price is not None and (
            source.marketer_price is None
            or source.maximum_sell_price is None
            or price < source.marketer_price
            or price > source.maximum_sell_price
        ):
            raise serializers.ValidationError({
                'price': 'Price must be within the seller approved range.'
            })
        if theme is not None and market is not None and theme.market_id != market.id:
            raise serializers.ValidationError({'theme': 'Theme must belong to this store.'})
        return attrs

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
            'status',
            'product',
            'images',
        ]
        read_only_fields = ('product', 'status')

class AffiliateProductDetailSerializer(serializers.ModelSerializer):
    product = AffiliateBankProductSerializer(read_only=True)
    required_product = AffiliateProductListSerializer(read_only=True)
    gift_product = AffiliateProductListSerializer(read_only=True)
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
