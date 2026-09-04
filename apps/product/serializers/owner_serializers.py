from rest_framework import serializers
from datetime import timedelta
from decimal import Decimal
from django.utils import timezone
from django.db import transaction
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field

from apps.product.models import (
    Product,
    ProductShipping,
    ProductTheme,
    ProductKeyword,
    ProductImage,
    ProductDiscount,
)
from apps.analytics.models import AnalyticsEvent
from apps.information.models import VoiceGuide
from apps.product.theme_layouts import product_theme_slot_count

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
    discount_type = serializers.ChoiceField(
        choices=(('none', 'None'), *ProductDiscount.TYPE_CHOICES),
        default='none',
        write_only=True,
    )
    discount_percentage = serializers.IntegerField(
        min_value=1, max_value=99, required=False, write_only=True,
    )
    discount_days = serializers.IntegerField(
        min_value=1, max_value=65535, required=False, write_only=True,
    )
    discount_people = serializers.IntegerField(
        min_value=1, max_value=65535, required=False, write_only=True,
    )
    discount_position = serializers.ChoiceField(
        choices=ProductDiscount.POSITION_CHOICES,
        default=ProductDiscount.TOP_LEFT,
        write_only=True,
    )
    theme = serializers.PrimaryKeyRelatedField(
        queryset=ProductTheme.objects.all(),
        required=False,
        write_only=True,
    )
    theme_index = serializers.IntegerField(
        min_value=1,
        max_value=4,
        required=False,
    )
    status = serializers.ChoiceField(
        choices=(Product.DRAFT, Product.QUEUE),
        default=Product.DRAFT,
    )
    main_price = serializers.DecimalField(
        max_digits=14,
        decimal_places=3,
        min_value=Decimal('0'),
    )
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
            'theme',
            'theme_index',
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
            'discount_type',
            'discount_percentage',
            'discount_days',
            'discount_people',
            'discount_position',
        ]
    @transaction.atomic
    def create(self, validated_data):
        discount_type = validated_data.pop('discount_type', 'none')
        discount_percentage = validated_data.pop('discount_percentage', None)
        discount_days = validated_data.pop('discount_days', None)
        discount_people = validated_data.pop('discount_people', None)
        discount_position = validated_data.pop(
            'discount_position', ProductDiscount.TOP_LEFT,
        )
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

        if discount_type != 'none':
            ProductDiscount.objects.create(
                product=product,
                discount_type=discount_type,
                percentage=discount_percentage,
                position=discount_position,
                duration=(
                    discount_days
                    if discount_type != ProductDiscount.PERCENT
                    else None
                ),
                expiry=(
                    timezone.now() + timedelta(days=discount_days)
                    if discount_type in (ProductDiscount.TIMED, ProductDiscount.GROUP)
                    else None
                ),
                limitation=(
                    discount_people if discount_type == ProductDiscount.GROUP else 0
                ),
            )

        return product

    def validate(self, attrs):
        attrs = super().validate(attrs)
        market = attrs.get('market')
        theme = attrs.get('theme')
        theme_index = attrs.get('theme_index')

        if market is not None and market.sales_channel == market.AFFILIATE:
            raise serializers.ValidationError({
                'market': 'Affiliate stores can only add products from the affiliate bank.'
            })

        is_marketer = attrs.get(
            'is_marketer', getattr(self.instance, 'is_marketer', False),
        )
        settlement_price = attrs.get(
            'marketer_price', getattr(self.instance, 'marketer_price', None),
        )
        maximum_sell_price = attrs.get(
            'maximum_sell_price',
            getattr(self.instance, 'maximum_sell_price', None),
        )
        if is_marketer:
            if settlement_price is None or maximum_sell_price is None:
                raise serializers.ValidationError({
                    'marketer_price': 'Seller settlement price is required.',
                    'maximum_sell_price': 'Maximum affiliate sale price is required.',
                })
            if settlement_price <= 0 or maximum_sell_price < settlement_price:
                raise serializers.ValidationError({
                    'maximum_sell_price': (
                        'Maximum sale price must be greater than or equal to the '
                        'seller settlement price.'
                    )
                })

        discount_type = attrs.get('discount_type', 'none')
        if discount_type != 'none' and attrs.get('discount_percentage') is None:
            raise serializers.ValidationError({
                'discount_percentage': 'Discount percentage is required.'
            })
        if (
            discount_type in (ProductDiscount.TIMED, ProductDiscount.GROUP)
            and attrs.get('discount_days') is None
        ):
            raise serializers.ValidationError({
                'discount_days': 'Discount duration is required.'
            })
        if (
            discount_type == ProductDiscount.GROUP
            and attrs.get('discount_people') is None
        ):
            raise serializers.ValidationError({
                'discount_people': 'Group customer capacity is required.'
            })

        product_type = attrs.get('type', getattr(self.instance, 'type', None))
        sell_type = attrs.get('sell_type', getattr(self.instance, 'sell_type', None))
        shipping_policy = attrs.get(
            'ship_cost_pay_type',
            getattr(self.instance, 'ship_cost_pay_type', None),
        )
        if (
            shipping_policy in (Product.STORE_SHIPPING, Product.CUSTOMER)
            and (product_type == Product.SERVICE or sell_type == Product.PERSON)
        ):
            raise serializers.ValidationError({
                'ship_cost_pay_type': (
                    'Store shipping is only available for physical goods sold online.'
                )
            })

        if (theme is None) != (theme_index is None):
            raise serializers.ValidationError({
                'theme': 'Theme and theme index must be provided together.'
            })
        if theme is not None and market is not None and theme.market_id != market.id:
            raise serializers.ValidationError({
                'theme': 'Theme must belong to the selected market.'
            })
        if theme is not None and theme_index is not None:
            if theme_index > product_theme_slot_count(theme.order):
                raise serializers.ValidationError({
                    'theme_index': 'The selected layout does not contain this slot.'
                })
            occupied_slot = Product.objects.filter(
                theme=theme,
                theme_index=str(theme_index),
            )
            if self.instance is not None:
                occupied_slot = occupied_slot.exclude(pk=self.instance.pk)
            if occupied_slot.exists():
                raise serializers.ValidationError({
                    'theme_index': 'This theme slot already contains a product.'
                })

        for field_name in ('required_product', 'gift_product'):
            related_product = attrs.get(field_name)
            if (
                related_product is not None
                and market is not None
                and related_product.market_id != market.id
            ):
                raise serializers.ValidationError({
                    field_name: 'Selected product must belong to the same market.'
                })
        return attrs

    def validate_ship_cost_pay_type(self, value):
        return Product.STORE_SHIPPING if value == Product.CUSTOMER else value

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        # Add existing images to response
        representation['images'] = [
            {'id': img.id, 'image': img.image.url} 
            for img in instance.images.all()  # Uses related_name
        ]
        return representation


class ProductUpdateSerializer(ProductCreateSerializer):
    class Meta(ProductCreateSerializer.Meta):
        fields = [
            field for field in ProductCreateSerializer.Meta.fields
            if field not in (
                'market',
                'status',
                'theme',
                'theme_index',
            )

        ]
        read_only_fields = ()

    @transaction.atomic
    def update(self, instance, validated_data):
        discount_type = validated_data.pop('discount_type', None)
        discount_percentage = validated_data.pop('discount_percentage', None)
        discount_days = validated_data.pop('discount_days', None)
        discount_people = validated_data.pop('discount_people', None)
        discount_position = validated_data.pop('discount_position', None)
        images = validated_data.pop('uploaded_images', [])

        product = serializers.ModelSerializer.update(
            self, instance, validated_data,
        )
        for image in images:
            ProductImage.objects.create(product=product, image=image)

        if discount_type is not None:
            product.automatic_discounts.update(is_active=False)
            if discount_type != 'none':
                ProductDiscount.objects.create(
                    product=product,
                    discount_type=discount_type,
                    percentage=discount_percentage,
                    position=discount_position or ProductDiscount.TOP_LEFT,
                    duration=(
                        discount_days
                        if discount_type != ProductDiscount.PERCENT else None
                    ),
                    expiry=(
                        timezone.now() + timedelta(days=discount_days)
                        if discount_type in (ProductDiscount.TIMED, ProductDiscount.GROUP)
                        else None
                    ),
                    limitation=(
                        discount_people
                        if discount_type == ProductDiscount.GROUP else 0
                    ),
                )
        return product


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


class ProductDiscountPresentationMixin(serializers.Serializer):
    discount_percentage = serializers.SerializerMethodField()
    discounted_price = serializers.SerializerMethodField()
    discount_type = serializers.SerializerMethodField()
    discount_position = serializers.SerializerMethodField()
    discount_days = serializers.SerializerMethodField()
    discount_people = serializers.SerializerMethodField()
    discount_remaining = serializers.SerializerMethodField()
    discount_expires_at = serializers.SerializerMethodField()

    def _active_discount(self, obj):
        cached = getattr(obj, '_active_product_discount', None)
        if cached is not None:
            return cached
        now = timezone.now()
        discounts = obj.automatic_discounts.filter(is_active=True).order_by(
            '-percentage', '-created_at',
        )
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        for discount in discounts:
            if discount.expiry and discount.expiry <= now:
                continue
            if discount.discount_type == ProductDiscount.GROUP:
                if discount.limitation <= discount.consumed + discount.reserved:
                    continue
                if user and user.is_authenticated and discount.users.filter(id=user.id).exists():
                    continue
            obj._active_product_discount = discount
            return discount
        return None

    @extend_schema_field(OpenApiTypes.INT)
    def get_discount_percentage(self, obj):
        discount = self._active_discount(obj)
        return discount.percentage if discount else 0

    @extend_schema_field(OpenApiTypes.STR)
    def get_discount_type(self, obj):
        discount = self._active_discount(obj)
        return discount.discount_type if discount else None

    @extend_schema_field(OpenApiTypes.STR)
    def get_discount_position(self, obj):
        discount = self._active_discount(obj)
        return discount.position if discount else None

    @extend_schema_field(OpenApiTypes.INT)
    def get_discount_days(self, obj):
        discount = self._active_discount(obj)
        return discount.duration if discount else None

    @extend_schema_field(OpenApiTypes.INT)
    def get_discount_people(self, obj):
        discount = self._active_discount(obj)
        return discount.limitation if discount else None

    @extend_schema_field(OpenApiTypes.INT)
    def get_discount_remaining(self, obj):
        discount = self._active_discount(obj)
        if not discount or discount.discount_type != ProductDiscount.GROUP:
            return None
        return max(0, discount.limitation - discount.consumed - discount.reserved)

    @extend_schema_field(OpenApiTypes.DATETIME)
    def get_discount_expires_at(self, obj):
        discount = self._active_discount(obj)
        return discount.expiry if discount else None

    @extend_schema_field(OpenApiTypes.DECIMAL)
    def get_discounted_price(self, obj):
        discount = self._active_discount(obj)
        if discount is None:
            return obj.main_price
        return (obj.main_price * (Decimal('100') - discount.percentage) / Decimal('100')).quantize(
            Decimal('0.001')
        )


class ProductListSerializer(ProductDiscountPresentationMixin, serializers.ModelSerializer):
    images = ProductImageSerializer(many=True)
    class Meta:
        model = Product
        fields = [
            'id',
            'name',
            'description',
            'main_price',
            'discount_percentage',
            'discounted_price',
            'discount_type',
            'discount_position',
            'discount_days',
            'discount_people',
            'discount_remaining',
            'discount_expires_at',
            'stock',
            'images',
        ]

class ProductWithIndexListSerializer(ProductDiscountPresentationMixin, serializers.ModelSerializer):
    images = ProductImageSerializer(many=True)
    class Meta:
        model = Product
        fields = [
            'id',
            'name',
            'description',
            'main_price',
            'discount_percentage',
            'discounted_price',
            'discount_type',
            'discount_position',
            'discount_days',
            'discount_people',
            'discount_remaining',
            'discount_expires_at',
            'stock',
            'images',
            'theme_index',
            # The mobile theme grid renders product labels from these.
            'tag',
            'tag_position',
        ]

class ProductDetailSerializer(ProductDiscountPresentationMixin, serializers.ModelSerializer):
    required_product = ProductListSerializer(read_only=True)
    gift_product = ProductListSerializer(read_only=True)
    keywords = KeywordField(many=True, read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)
    
    # Handle shipping cost
    shipping_cost = serializers.SerializerMethodField()
    
    # Handle comments count (since GenericRelation might be complex)
    comments_count = serializers.SerializerMethodField()
    likes_count = serializers.SerializerMethodField()
    views_count = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()
    is_bookmarked = serializers.SerializerMethodField()
    voice_guide_url = serializers.SerializerMethodField()
    market_business_id = serializers.CharField(
        source='market.business_id', read_only=True,
    )

    class Meta:
        model = Product
        fields = [
            'id',
            'market',
            'theme',
            'theme_index',
            'type',
            'name',
            'description',
            'technical_detail',
            'sub_category',
            'keywords',
            'stock',
            'main_price',
            'discount_percentage',
            'discounted_price',
            'discount_type',
            'discount_position',
            'discount_days',
            'discount_people',
            'discount_remaining',
            'discount_expires_at',
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
            'likes_count',
            'views_count',
            'is_liked',
            'is_bookmarked',
            'voice_guide_url',
            'market_business_id',
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

    @extend_schema_field(OpenApiTypes.INT)
    def get_likes_count(self, obj):
        return obj.liked_by.filter(is_active=True).count()

    @extend_schema_field(OpenApiTypes.INT)
    def get_views_count(self, obj):
        return obj.analytics_events.filter(
            event_type=AnalyticsEvent.PRODUCT_VIEW,
        ).count()

    @extend_schema_field(OpenApiTypes.BOOL)
    def get_is_liked(self, obj):
        user = getattr(self.context.get('request'), 'user', None)
        return bool(
            user and user.is_authenticated
            and obj.liked_by.filter(user=user, is_active=True).exists()
        )

    @extend_schema_field(OpenApiTypes.BOOL)
    def get_is_bookmarked(self, obj):
        user = getattr(self.context.get('request'), 'user', None)
        return bool(
            user and user.is_authenticated
            and obj.bookmarked_by.filter(user=user, is_active=True).exists()
        )

    @extend_schema_field(OpenApiTypes.URI)
    def get_voice_guide_url(self, obj):
        guide = VoiceGuide.objects.first()
        if not guide or not guide.product_file:
            return None
        request = self.context.get('request')
        return request.build_absolute_uri(guide.product_file.url) if request else guide.product_file.url


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
    client_request_id = serializers.UUIDField(write_only=True, required=False)

    class Meta:
        model = ProductTheme
        fields = [
            'name',
            'order',
            'client_request_id',
        ]

    def create(self, validated_data):
        validated_data['name'] = f"layout-{validated_data['order']}"
        return super().create(validated_data)


class ProductThemeUpdateSerializer(serializers.Serializer):
    product = serializers.UUIDField()
    index = serializers.IntegerField(min_value=1, max_value=4)


class ProductThemeLayoutSerializer(serializers.Serializer):
    order = serializers.IntegerField(min_value=0, max_value=17)


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
