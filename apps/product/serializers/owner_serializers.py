from rest_framework import serializers
from decimal import Decimal
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field

from apps.product.models import (
    Product,
    ProductShipping,
    ProductTheme,
    ProductKeyword,
    ProductImage,
)

@extend_schema_field(OpenApiTypes.STR)
class KeywordField(serializers.RelatedField):

    def to_representation(self, value):
        return value.name

    def to_internal_value(self, data):
        keyword_obj, created = ProductKeyword.objects.get_or_create(name=data.strip())
        return keyword_obj
    
class ProductImageSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(read_only=True)

    class Meta:
        model = ProductImage
        fields = [
            'id',
            'image'
        ]


class ProductCreateSerializer(serializers.ModelSerializer):
    keywords = KeywordField(
        many=True,
        queryset=ProductKeyword.objects.all(),
        required=False
    )
    type = serializers.ChoiceField(
        choices=Product.TYPE_CHOICES,
    )
    tag = serializers.ChoiceField(
        choices=Product.TAG_CHOICES,
        default=Product.NONE,
    )
    tag_position = serializers.ChoiceField(
        choices=Product.TAG_POSITION_CHOICES,
        default=Product.TOP_LEFT,
    )
    sell_type = serializers.ChoiceField(
        choices=Product.SELL_TYPE_CHOICES,
        default=Product.ONLINE,
    )
    ship_cost_pay_type = serializers.ChoiceField(
        choices=Product.SHIP_COST_PAY_TYPE_CHOICES,
    )
    uploaded_images = serializers.ListField(
        child=serializers.ImageField(allow_empty_file=False), 
        required=False,
        write_only=True
    )

    class Meta:
        model = Product
        fields = [
            'market',
            'type',
            'name',
            'description',
            'technical_detail',
            'sub_category',
            'keywords',
            'stock',
            'main_price',
            'colleague_price',
            'marketer_price',
            'maximum_sell_price',
            'required_product',
            'gift_product',
            'is_marketer',
            'is_requirement',
            'status',
            'tag',
            'tag_position',
            'sell_type',
            # 'ship_cost',
            'ship_cost_pay_type',
            'uploaded_images',
        ]

    def create(self, validated_data):
        # remove images 
        images = validated_data.pop('uploaded_images', [])

        keywords_data = validated_data.pop('keywords', [])
        product = Product.objects.create(**validated_data)

        product.keywords.set(keywords_data)
        
        for image in images:
            _ = ProductImage.objects.create(
                product=product,
                image=image
            )

        return product

    def validate_ship_cost_pay_type(self, value):
        if value == Product.CUSTOMER:
            raise serializers.ValidationError(
                "Customer-paid shipping is unavailable until checkout can select and snapshot it."
            )
        return value

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        # Add existing images to response
        representation['images'] = [
            {'id': img.id, 'image': img.image.url} 
            for img in instance.images.all()  # Uses related_name
        ]
        return representation


class ProductCreateDataSerializer(ProductCreateSerializer):
    product = serializers.UUIDField()

    class Meta(ProductCreateSerializer.Meta):
        fields = ['product', *ProductCreateSerializer.Meta.fields]


class ProductCreateEnvelopeSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    code = serializers.IntegerField()
    data = ProductCreateDataSerializer()
    message = serializers.CharField()


class ProductShippingCreateSerializer(serializers.ModelSerializer):
    product = serializers.UUIDField(read_only=True)
    name = serializers.CharField(max_length=64)
    price = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal("0"),
    )

    class Meta:
        model = ProductShipping
        fields = ('product', 'name', 'price', )

class ProductShipListSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductShipping
        fields = ('id', 'product', 'name', 'price', )


class ProductShipListEnvelopeSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    code = serializers.IntegerField()
    data = ProductShipListSerializer(many=True)
    message = serializers.CharField()
        
class ProductListSerializer(serializers.ModelSerializer):
    images = ProductImageSerializer(many=True)
    class Meta:
        model = Product
        fields = [
            'id',
            'name',
            'description',
            'main_price',
            'stock',
            'images',
        ]

class ProductWithIndexListSerializer(serializers.ModelSerializer):
    images = ProductImageSerializer(many=True)
    class Meta:
        model = Product
        fields = [
            'id',
            'name',
            'description',
            'main_price',
            'stock',
            'images',
            'theme_index',
            # The mobile theme grid renders product labels from these.
            'tag',
            'tag_position',
        ]

class ProductDetailSerializer(serializers.ModelSerializer):
    required_product = ProductListSerializer(read_only=True)
    gift_product = ProductListSerializer(read_only=True)
    keywords = KeywordField(many=True, read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)
    
    # Handle shipping cost
    shipping_cost = serializers.SerializerMethodField()
    
    # Handle comments count (since GenericRelation might be complex)
    comments_count = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id',
            'name',
            'description',
            'technical_detail',
            'keywords',
            'stock',
            'main_price',
            'colleague_price',
            'marketer_price',
            'maximum_sell_price',
            'required_product',
            'gift_product',
            'is_marketer',
            'marketer_price',
            'tag',
            'tag_position',
            'sell_type',
            'ship_cost_pay_type',
            'shipping_cost',
            'images',
            'comments_count',
            'status',
            'created_at',
            'updated_at',
        ]

    @extend_schema_field(ProductShipListSerializer(many=True))
    def get_shipping_cost(self, obj):
        """Legacy options are informational until checkout gains a selection model."""
        return ProductShipListSerializer(obj.ships.all(), many=True).data

    @extend_schema_field(serializers.IntegerField())
    def get_comments_count(self, obj):
        return obj.comments.count()


class ProductDetailEnvelopeSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    code = serializers.IntegerField()
    data = ProductDetailSerializer()
    message = serializers.CharField()

class ProductThemeListSerializer(serializers.ModelSerializer):
    products = serializers.SerializerMethodField()

    class Meta:
        model = ProductTheme
        fields = [
            'id',
            'name',
            'order',
            'products',
        ]

    @extend_schema_field(ProductWithIndexListSerializer(many=True))
    def get_products(self, obj):
        products = obj.products.all()
        return ProductWithIndexListSerializer(products, many=True, context=self.context).data


class ProductThemeCreateSerializer(serializers.ModelSerializer):
    name = serializers.CharField(read_only=True)
    order = serializers.IntegerField(min_value=0, max_value=17)

    class Meta:
        model = ProductTheme
        fields = [
            'name',
            'order',
        ]

    def create(self, validated_data):
        validated_data['name'] = f"layout-{validated_data['order']}"
        return super().create(validated_data)


class ProductThemeUpdateSerializer(serializers.Serializer):
    product = serializers.UUIDField()
    index = serializers.IntegerField(min_value=1, max_value=4)


class ProductThemeCreateEnvelopeSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    code = serializers.IntegerField()
    data = ProductThemeCreateSerializer()
    message = serializers.CharField()


class ProductThemeListEnvelopeSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    code = serializers.IntegerField()
    data = ProductThemeListSerializer(many=True)
    message = serializers.CharField()


class ProductThemeUpdateEnvelopeSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    code = serializers.IntegerField()
    data = serializers.DictField()
    message = serializers.CharField()
