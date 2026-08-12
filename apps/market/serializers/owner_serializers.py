from rest_framework import serializers
from django.urls import reverse
import jdatetime

from apps.market.models import (
    Market,
    MarketLocation,
    MarketContact,
    MarketSlider,
    MarketTheme,
)


class MarketCreateSerializer(serializers.ModelSerializer):
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
    class Meta:
        model = MarketLocation
        fields = [
            'city',
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
            'is_paid',
            'created_at',
            'inactive_url',
            'queue_url',
            'logo_img',
            'background_img',
            'theme',
            'view_count',
        ]

    def get_created_at(self, obj):
        created_at_date = obj.created_at.date()
        jalali_date = jdatetime.date.fromgregorian(date=created_at_date)
        return jalali_date.strftime("%Y/%m/%d")

    def get_inactive_url(self, obj):
        request = self.context.get('request')
        return request.build_absolute_uri(
            reverse(
                'market_owner:inactive',
                kwargs={'pk': obj.id},
            )
        )

    def get_queue_url(self, obj):
        request = self.context.get('request')
        return request.build_absolute_uri(
            reverse(
                'market_owner:queue',
                kwargs={'pk': obj.id},
            )
        )

    def get_sub_category_title(self, obj):
        return obj.sub_category.title if obj.sub_category else None

    def get_view_count(self, obj):
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
