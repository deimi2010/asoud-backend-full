from rest_framework import serializers
import jdatetime
from drf_spectacular.utils import extend_schema_field
from typing import Optional

from apps.market.models import (
    Market,
    MarketReport,
    MarketContact,
    MarketLocation
)


class MarketListSerializer(serializers.ModelSerializer):
    created_at = serializers.SerializerMethodField()
    sub_category_title = serializers.SerializerMethodField()
    view_count = serializers.SerializerMethodField()

    # theme = MarketThemeCreateSerializer()

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
            'logo_img',
            'background_img',
            # 'theme',
            'view_count',
        ]

    @extend_schema_field(serializers.CharField())
    def get_created_at(self, obj) -> str:
        created_at_date = obj.created_at.date()
        jalali_date = jdatetime.date.fromgregorian(date=created_at_date)
        return jalali_date.strftime("%Y/%m/%d")

    @extend_schema_field(serializers.CharField())
    def get_sub_category_title(self, obj) -> Optional[str]:
        return obj.sub_category.title if obj.sub_category else None

    @extend_schema_field(serializers.IntegerField())
    def get_view_count(self, obj) -> int:
        market_viewed_by = obj.viewed_by.all()
        return market_viewed_by.count()


class MarketBookmarkUpdateSerializer(serializers.Serializer):
    bookmarked = serializers.BooleanField()


class MarketBookmarkStateSerializer(serializers.Serializer):
    market_id = serializers.UUIDField()
    bookmarked = serializers.BooleanField()


class MarketBookmarkEnvelopeSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    code = serializers.IntegerField()
    data = MarketBookmarkStateSerializer()
    message = serializers.CharField()


class MarketBookmarkListEnvelopeSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    code = serializers.IntegerField()
    data = MarketListSerializer(many=True)
    message = serializers.CharField()


class MarketReportCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = MarketReport
        fields = [
            'description',
        ]

class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = MarketLocation
        fields = [
            'city',
            'address',
            'zip_code',
            'latitude',
            'longitude',
        ]

class ContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = MarketContact
        fields = [
            'first_mobile_number',
            'second_mobile_number',
            'telephone',
            'email',
            'messenger_ids',
        ]

class MarketDetailSerializer(serializers.ModelSerializer):
    location = LocationSerializer()
    contact = ContactSerializer()
    created_at = serializers.SerializerMethodField()
    sub_category_title = serializers.SerializerMethodField()
    view_count = serializers.SerializerMethodField()
    
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
            'logo_img',
            'background_img',
            'description',
            'location',
            'contact',
            'view_count',
        ]

    @extend_schema_field(serializers.CharField())
    def get_created_at(self, obj) -> str:
        created_at_date = obj.created_at.date()
        jalali_date = jdatetime.date.fromgregorian(date=created_at_date)
        return jalali_date.strftime("%Y/%m/%d")

    @extend_schema_field(serializers.CharField())
    def get_sub_category_title(self, obj) -> Optional[str]:
        return obj.sub_category.title if obj.sub_category else None

    @extend_schema_field(serializers.IntegerField())
    def get_view_count(self, obj) -> int:
        market_viewed_by = obj.viewed_by.all()
        return market_viewed_by.count()
