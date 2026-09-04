from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from apps.category.models import SubCategory
from apps.market.models import (
    BusinessCardProfile,
    BusinessCardTariff,
    Market,
    MarketContact,
    MarketLocation,
)
from apps.market.serializers.owner_serializers import (
    MarketCreateSerializer,
    MarketUpdateSerializer,
)
from apps.region.models import City


class BusinessCardWriteSerializer(serializers.Serializer):
    type = serializers.ChoiceField(choices=Market.TYPE_CHOICES, required=False)
    sales_channel = serializers.ChoiceField(
        choices=Market.SALES_CHANNEL_CHOICES,
        required=False,
        default=Market.SELLER,
    )
    business_id = serializers.CharField(max_length=63, required=False)
    name = serializers.CharField(max_length=100, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    national_code = serializers.CharField(required=False, allow_blank=True, max_length=10)
    sub_category = serializers.PrimaryKeyRelatedField(
        queryset=SubCategory.objects.all(), required=False,
    )
    slogan = serializers.CharField(required=False, allow_blank=True, max_length=100)
    first_mobile_number = serializers.CharField(required=False, max_length=15)
    second_mobile_number = serializers.CharField(required=False, allow_blank=True, max_length=15)
    telephone = serializers.CharField(required=False, allow_blank=True, max_length=15)
    fax = serializers.CharField(required=False, allow_blank=True, max_length=15)
    email = serializers.EmailField(required=False, allow_blank=True, max_length=64)
    website_url = serializers.CharField(required=False, allow_blank=True, max_length=64)
    messenger_ids = serializers.DictField(required=False, allow_null=True)
    city = serializers.PrimaryKeyRelatedField(queryset=City.objects.all(), required=False)
    address = serializers.CharField(required=False, allow_blank=True)
    zip_code = serializers.CharField(required=False, allow_blank=True, max_length=15)
    latitude = serializers.DecimalField(required=False, max_digits=9, decimal_places=6)
    longitude = serializers.DecimalField(required=False, max_digits=9, decimal_places=6)

    required_on_create = (
        'type', 'business_id', 'name', 'sub_category', 'first_mobile_number',
        'city', 'address', 'zip_code', 'latitude', 'longitude',
    )

    def validate_website_url(self, value):
        if not value:
            return value
        normalized = value if '://' in value else f'https://{value}'
        return serializers.URLField(max_length=64).run_validation(normalized)

    def validate(self, attrs):
        if self.instance is None:
            missing = [field for field in self.required_on_create if field not in attrs]
            if missing:
                raise serializers.ValidationError({field: 'This field is required.' for field in missing})
        return attrs

    @staticmethod
    def _split(attrs):
        market_fields = {
            'type', 'sales_channel', 'business_id', 'name', 'description',
            'national_code', 'sub_category', 'slogan',
        }
        contact_fields = {
            'first_mobile_number', 'second_mobile_number', 'telephone', 'fax',
            'email', 'website_url', 'messenger_ids',
        }
        location_fields = {'city', 'address', 'zip_code', 'latitude', 'longitude'}
        return (
            {key: value for key, value in attrs.items() if key in market_fields},
            {key: value for key, value in attrs.items() if key in contact_fields},
            {key: value for key, value in attrs.items() if key in location_fields},
        )

    @transaction.atomic
    def create(self, validated_data):
        market_data, contact_data, location_data = self._split(validated_data)
        serializer_data = dict(market_data)
        if 'sub_category' in serializer_data:
            serializer_data['sub_category'] = serializer_data['sub_category'].pk
        market_serializer = MarketCreateSerializer(data=serializer_data)
        market_serializer.is_valid(raise_exception=True)
        market = market_serializer.save(user=self.context['request'].user)
        MarketContact.objects.create(market=market, **contact_data)
        MarketLocation.objects.create(market=market, **location_data)
        return market.business_card

    @transaction.atomic
    def update(self, instance, validated_data):
        card = BusinessCardProfile.objects.select_for_update().select_related('market').get(pk=instance.pk)
        market_data, contact_data, location_data = self._split(validated_data)
        if market_data:
            serializer_data = dict(market_data)
            if 'sub_category' in serializer_data:
                serializer_data['sub_category'] = serializer_data['sub_category'].pk
            market_serializer = MarketUpdateSerializer(
                card.market, data=serializer_data, partial=True,
            )
            market_serializer.is_valid(raise_exception=True)
            market_serializer.save()
        if contact_data:
            MarketContact.objects.update_or_create(
                market=card.market, defaults=contact_data,
            )
        if location_data:
            current = MarketLocation.objects.filter(market=card.market).first()
            if current is None:
                required = {'city', 'address', 'zip_code', 'latitude', 'longitude'}
                missing = required - location_data.keys()
                if missing:
                    raise serializers.ValidationError(
                        {field: 'This field is required.' for field in missing}
                    )
                MarketLocation.objects.create(market=card.market, **location_data)
            else:
                for key, value in location_data.items():
                    setattr(current, key, value)
                current.save()
        return card


class BusinessCardSerializer(serializers.ModelSerializer):
    market_id = serializers.UUIDField(source='market.id', read_only=True)
    business_id = serializers.CharField(source='market.business_id', read_only=True)
    name = serializers.CharField(source='market.name', read_only=True)
    type = serializers.CharField(source='market.type', read_only=True)
    sales_channel = serializers.CharField(source='market.sales_channel', read_only=True)
    description = serializers.CharField(source='market.description', read_only=True)
    national_code = serializers.CharField(source='market.national_code', read_only=True)
    slogan = serializers.CharField(source='market.slogan', read_only=True)
    sub_category = serializers.UUIDField(source='market.sub_category_id', read_only=True)
    sub_category_title = serializers.CharField(source='market.sub_category.title', read_only=True)
    category = serializers.UUIDField(source='market.sub_category.category_id', read_only=True)
    category_title = serializers.CharField(
        source='market.sub_category.category.title', read_only=True,
    )
    group = serializers.UUIDField(
        source='market.sub_category.category.group_id', read_only=True,
    )
    group_title = serializers.CharField(
        source='market.sub_category.category.group.title', read_only=True,
    )
    logo_img = serializers.SerializerMethodField()
    background_img = serializers.SerializerMethodField()
    contact = serializers.SerializerMethodField()
    location = serializers.SerializerMethodField()
    subscription_fee = serializers.SerializerMethodField()
    subscription_active = serializers.SerializerMethodField()
    public_url = serializers.SerializerMethodField()

    class Meta:
        model = BusinessCardProfile
        fields = (
            'id', 'market_id', 'business_id', 'name', 'type', 'sales_channel',
            'description', 'national_code', 'slogan', 'sub_category',
            'sub_category_title', 'category', 'category_title', 'group',
            'group_title', 'logo_img', 'background_img', 'contact',
            'location', 'status', 'status_reason', 'is_paid',
            'subscription_start_date', 'subscription_end_date',
            'subscription_fee', 'subscription_active', 'public_url',
            'created_at', 'updated_at',
        )

    def _file_url(self, field):
        if not field:
            return None
        request = self.context.get('request')
        return request.build_absolute_uri(field.url) if request else field.url

    def get_logo_img(self, obj) -> str | None:
        return self._file_url(obj.market.logo_img)

    def get_background_img(self, obj) -> str | None:
        return self._file_url(obj.market.background_img)

    def get_contact(self, obj) -> dict | None:
        try:
            contact = obj.market.contact
        except MarketContact.DoesNotExist:
            return None
        return {
            'first_mobile_number': contact.first_mobile_number,
            'second_mobile_number': contact.second_mobile_number,
            'telephone': contact.telephone,
            'fax': contact.fax,
            'email': contact.email,
            'website_url': contact.website_url,
            'messenger_ids': contact.messenger_ids or {},
        }

    def get_location(self, obj) -> dict | None:
        try:
            location = obj.market.location
        except MarketLocation.DoesNotExist:
            return None
        return {
            'city': str(location.city_id),
            'city_name': location.city.name,
            'province': str(location.city.province_id),
            'province_name': location.city.province.name,
            'country': str(location.city.province.country_id),
            'country_name': location.city.province.country.name,
            'address': location.address,
            'zip_code': location.zip_code,
            'latitude': location.latitude,
            'longitude': location.longitude,
        }

    def get_subscription_fee(self, obj) -> str | None:
        tariff = BusinessCardTariff.objects.filter(is_active=True).first()
        return str(tariff.amount) if tariff else None

    def get_subscription_active(self, obj) -> bool:
        return bool(
            obj.is_paid
            and (
                obj.subscription_end_date is None
                or obj.subscription_end_date > timezone.now()
            )
        )

    def get_public_url(self, obj) -> str:
        base = getattr(settings, 'PUBLIC_APP_URL', 'https://asoud.ir').rstrip('/')
        return f'{base}/card/{obj.market.business_id}'
