import re

from rest_framework import serializers
from django.urls import reverse
import jdatetime

from apps.market.models import (
    Market,
    MarketLocation,
    MarketContact,
    MarketSlider,
    MarketTheme,
    MarketGatewayConnection,
)


class MarketCreateSerializer(serializers.ModelSerializer):
    def validate_business_id(self, value):
        normalized = value.strip().lower()
        if not re.fullmatch(r'[a-z](?:[a-z0-9-]{3,61}[a-z0-9])', normalized):
            raise serializers.ValidationError(
                'Business ID must be a 5-63 character lowercase subdomain label.'
            )
        if '--' in normalized:
            raise serializers.ValidationError(
                'Business ID cannot contain consecutive hyphens.'
            )
        return normalized

    class Meta:
        model = Market
        fields = [
            'type',
            'business_id',
            'name',
            'description',
            'national_code',
            'sub_category',
            'slogan',
        ]


class MarketUpdateSerializer(MarketCreateSerializer):
    def update(self, instance, validated_data):
        return super().update(instance, validated_data)


class MarketLocationCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = MarketLocation
        fields = [
            'market',
            'city',
            'address',
            'zip_code',
            'latitude',
            'longitude',
        ]


class MarketLocationUpdateSerializer(serializers.ModelSerializer):
    city_name = serializers.CharField(source='city.name', read_only=True)
    province = serializers.UUIDField(source='city.province_id', read_only=True)
    province_name = serializers.CharField(source='city.province.name', read_only=True)
    country = serializers.UUIDField(source='city.province.country_id', read_only=True)
    country_name = serializers.CharField(source='city.province.country.name', read_only=True)

    class Meta:
        model = MarketLocation
        fields = [
            'city',
            'city_name',
            'province',
            'province_name',
            'country',
            'country_name',
            'address',
            'zip_code',
            'latitude',
            'longitude',
        ]

    def update(self, instance, validated_data):
        return super().update(instance, validated_data)


class MarketContactCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = MarketContact
        fields = [
            'market',
            'first_mobile_number',
            'second_mobile_number',
            'telephone',
            'fax',
            'email',
            'website_url',
            'messenger_ids',
        ]


class MarketContactUpdaterSerializer(serializers.ModelSerializer):
    class Meta:
        model = MarketContact
        fields = [
            'first_mobile_number',
            'second_mobile_number',
            'telephone',
            'fax',
            'email',
            'website_url',
            'messenger_ids',
        ]


class MarketThemeCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = MarketTheme
        fields = [
            'color',
            'secondary_color',
            'background_color',
            'font',
            'font_color',
            'secondary_font_color',
        ]


class MarketGatewayConnectionSerializer(serializers.ModelSerializer):
    user_code = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True,
        max_length=255,
    )
    has_user_code = serializers.SerializerMethodField()

    class Meta:
        model = MarketGatewayConnection
        fields = [
            'gateway_type',
            'user_code',
            'has_user_code',
            'status',
        ]
        read_only_fields = ['status', 'has_user_code']

    def validate(self, attrs):
        gateway_type = attrs.get(
            'gateway_type',
            getattr(self.instance, 'gateway_type', None),
        )
        user_code = attrs.get(
            'user_code',
            getattr(self.instance, 'user_code', ''),
        ).strip()
        if gateway_type == MarketGatewayConnection.PERSONAL and not user_code:
            raise serializers.ValidationError({
                'user_code': 'Personal gateway user code is required.'
            })
        attrs['user_code'] = (
            user_code if gateway_type == MarketGatewayConnection.PERSONAL else ''
        )
        return attrs

    def get_has_user_code(self, obj):
        return bool(obj.user_code)


class MarketListSerializer(serializers.ModelSerializer):
    created_at = serializers.SerializerMethodField()
    inactive_url = serializers.SerializerMethodField()
    queue_url = serializers.SerializerMethodField()
    sub_category_title = serializers.SerializerMethodField()
    view_count = serializers.SerializerMethodField()

    theme = MarketThemeCreateSerializer()

    class Meta:
        model = Market
        fields = [
            'id',
            'business_id',
            'name',
            'sub_category',
            'sub_category_title',
            'status',
            'status_reason',
            'is_paid',
            'created_at',
            'inactive_url',
            'queue_url',
            'logo_img',
            'background_img',
            'theme',
            'view_count',
        ]

    def get_created_at(self, obj) -> str:
        created_at_date = obj.created_at.date()
        jalali_date = jdatetime.date.fromgregorian(date=created_at_date)
        return jalali_date.strftime("%Y/%m/%d")

    def get_inactive_url(self, obj) -> str:
        request = self.context.get('request')
        return request.build_absolute_uri(
            reverse(
                'market_owner:inactive',
                kwargs={'pk': obj.id},
            )
        )

    def get_queue_url(self, obj) -> str:
        request = self.context.get('request')
        return request.build_absolute_uri(
            reverse(
                'market_owner:queue',
                kwargs={'pk': obj.id},
            )
        )

    def get_sub_category_title(self, obj) -> str | None:
        return obj.sub_category.title if obj.sub_category else None

    def get_view_count(self, obj) -> int:
        market_viewed_by = obj.viewed_by.all()
        return market_viewed_by.count()


class MarketSliderListSerializer(serializers.ModelSerializer):
    class Meta:
        model = MarketSlider
        fields = [
            'id',
            'image',
            'url',
        ]
