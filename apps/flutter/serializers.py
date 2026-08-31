from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.shortcuts import get_current_site
from django_comments_xtd.models import XtdComment
from rest_framework import serializers
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field

from apps.market.models import Market
from apps.market.models import MarketReport
from apps.market.serializers.user_serializers import ContactSerializer, LocationSerializer
from apps.product.models import Product
from apps.analytics.models import AnalyticsEvent
from apps.information.models import VoiceGuide
from apps.product.serializers.owner_serializers import (
    ProductDetailSerializer,
    ProductListSerializer,
)


def _public_comment_count(obj, request):
    site_id = get_current_site(request).id if request else None
    filters = {
        'content_type': ContentType.objects.get_for_model(obj),
        'object_pk': str(obj.id),
        'is_public': True,
        'is_removed': False,
    }
    if site_id is not None:
        filters['site_id'] = site_id
    return XtdComment.objects.filter(**filters).count()


class PublicProductDetailSerializer(ProductDetailSerializer):
    """Customer-safe product details without owner pricing or workflow fields."""

    required_product = serializers.SerializerMethodField()
    gift_product = serializers.SerializerMethodField()
    market_id = serializers.UUIDField(read_only=True)
    market_business_id = serializers.CharField(
        source='market.business_id', read_only=True,
    )
    comments_count = serializers.SerializerMethodField()
    likes_count = serializers.SerializerMethodField()
    views_count = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()
    is_bookmarked = serializers.SerializerMethodField()
    voice_guide_url = serializers.SerializerMethodField()

    class Meta(ProductDetailSerializer.Meta):
        fields = [
            'id',
            'name',
            'type',
            'description',
            'technical_detail',
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
            'required_product',
            'gift_product',
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
            'market_id',
            'market_business_id',
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

    @extend_schema_field(OpenApiTypes.INT)
    def get_comments_count(self, obj):
        return _public_comment_count(obj, self.context.get('request'))

    @extend_schema_field(OpenApiTypes.INT)
    def get_likes_count(self, obj):
        return obj.liked_by.filter(is_active=True).count()

    @extend_schema_field(OpenApiTypes.INT)
    def get_views_count(self, obj):
        return AnalyticsEvent.objects.filter(
            product=obj,
            event_type=AnalyticsEvent.PRODUCT_VIEW,
        ).count()

    def _user_state(self, obj, relation):
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        if not user or not user.is_authenticated:
            return False
        return relation.filter(user=user, is_active=True).exists()

    @extend_schema_field(OpenApiTypes.BOOL)
    def get_is_liked(self, obj):
        return self._user_state(obj, obj.liked_by)

    @extend_schema_field(OpenApiTypes.BOOL)
    def get_is_bookmarked(self, obj):
        return self._user_state(obj, obj.bookmarked_by)

    @extend_schema_field(OpenApiTypes.URI)
    def get_voice_guide_url(self, obj):
        guide = VoiceGuide.objects.first()
        if not guide or not guide.product_file:
            return None
        request = self.context.get('request')
        return request.build_absolute_uri(guide.product_file.url) if request else guide.product_file.url


class ProductDetailQuerySerializer(serializers.Serializer):
    id = serializers.UUIDField()


class PublicProductDetailEnvelopeSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    code = serializers.IntegerField()
    data = PublicProductDetailSerializer()


class ProductLikeActionSerializer(serializers.Serializer):
    is_liked = serializers.BooleanField(read_only=True)
    likes_count = serializers.IntegerField(read_only=True)


class ProductBookmarkActionSerializer(serializers.Serializer):
    is_bookmarked = serializers.BooleanField(read_only=True)


class ProductReportActionSerializer(serializers.Serializer):
    description = serializers.CharField(max_length=2000, write_only=True)
    submitted = serializers.BooleanField(read_only=True)


class PublicMarketInteractionSerializer(serializers.ModelSerializer):
    comments_count = serializers.SerializerMethodField()
    likes_count = serializers.SerializerMethodField()
    views_count = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()
    is_bookmarked = serializers.SerializerMethodField()
    voice_guide_url = serializers.SerializerMethodField()
    contact = ContactSerializer(read_only=True)
    location = LocationSerializer(read_only=True)

    class Meta:
        model = Market
        fields = (
            'id', 'business_id', 'name', 'comments_count', 'likes_count',
            'views_count', 'is_liked', 'is_bookmarked', 'voice_guide_url',
            'contact', 'location',
        )

    @extend_schema_field(OpenApiTypes.INT)
    def get_comments_count(self, obj):
        return _public_comment_count(obj, self.context.get('request'))

    @extend_schema_field(OpenApiTypes.INT)
    def get_likes_count(self, obj):
        return obj.liked_by.filter(is_active=True).count()

    @extend_schema_field(OpenApiTypes.INT)
    def get_views_count(self, obj):
        return obj.viewed_by.count()

    def _user_state(self, obj, relation):
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        if not user or not user.is_authenticated:
            return False
        return relation.filter(user=user, is_active=True).exists()

    @extend_schema_field(OpenApiTypes.BOOL)
    def get_is_liked(self, obj):
        return self._user_state(obj, obj.liked_by)

    @extend_schema_field(OpenApiTypes.BOOL)
    def get_is_bookmarked(self, obj):
        return self._user_state(obj, obj.bookmarked_by)

    @extend_schema_field(OpenApiTypes.URI)
    def get_voice_guide_url(self, obj):
        guide = VoiceGuide.objects.first()
        if not guide or not guide.market_file:
            return None
        request = self.context.get('request')
        return request.build_absolute_uri(guide.market_file.url) if request else guide.market_file.url


class MarketLikeActionSerializer(serializers.Serializer):
    is_liked = serializers.BooleanField(read_only=True)
    likes_count = serializers.IntegerField(read_only=True)


class MarketBookmarkActionSerializer(serializers.Serializer):
    is_bookmarked = serializers.BooleanField(read_only=True)


class MarketReportActionSerializer(serializers.ModelSerializer):
    submitted = serializers.BooleanField(read_only=True)

    class Meta:
        model = MarketReport
        fields = ('description', 'submitted')
