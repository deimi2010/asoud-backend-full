from typing import Any, Dict

from drf_spectacular.utils import extend_schema_field
from jdatetime import datetime as jdatetime
from rest_framework import serializers

from apps.advertise.models import Advertisement, AdvImage, AdvKeyword
from apps.product.models import Product


class AdvertiseImageSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(read_only=True)

    class Meta:
        model = AdvImage
        fields = ['id', 'image']


class AdvertiseSerializer(serializers.ModelSerializer):
    product = serializers.PrimaryKeyRelatedField(read_only=True)
    user = serializers.SerializerMethodField()
    images = AdvertiseImageSerializer(many=True, read_only=True)

    class Meta:
        model = Advertisement
        fields = [
            'id',
            'user',
            'type',
            'name',
            'description',
            'category',
            'province',
            'city',
            'email',
            'keywords',
            'price',
            'product',
            'is_paid',
            'images',
            'created_at',
            'updated_at',
        ]

    def get_user(self, obj) -> dict:
        return {'id': str(obj.user_id)}


class AdvertiseCreateSerializer(serializers.ModelSerializer):
    product = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(),
        required=False,
        allow_null=True,
    )
    keywords = serializers.ListField(
        child=serializers.CharField(max_length=50),
        required=False,
    )
    images = serializers.ListField(child=serializers.ImageField(), required=False)
    is_paid = serializers.BooleanField(read_only=True)

    class Meta:
        model = Advertisement
        fields = [
            'type',
            'name',
            'description',
            'category',
            'province',
            'city',
            'email',
            'keywords',
            'price',
            'product',
            'is_paid',
            'images',
        ]
        extra_kwargs = {
            'type': {'required': False},
            'name': {'required': False},
            'description': {'required': False},
            'category': {'required': False},
            'price': {'required': False},
        }

    def validate(self, attrs):
        product = attrs.get('product')
        owner = self.context.get('owner')
        request = self.context.get('request')
        owner = owner or getattr(request, 'user', None)
        if product and (owner is None or product.market.user_id != owner.id):
            raise serializers.ValidationError({'product': 'Product not found.'})
        if self.instance and product and product.id != self.instance.product_id:
            raise serializers.ValidationError({'product': 'Product cannot be changed.'})
        if not product and not self.instance:
            missing = [field for field in ('type', 'name', 'description') if not attrs.get(field)]
            if missing:
                raise serializers.ValidationError(
                    {field: 'This field is required.' for field in missing}
                )
        if 'keywords' in attrs:
            keywords = [value.strip() for value in attrs['keywords'] if value.strip()]
            if len(keywords) > 20:
                raise serializers.ValidationError({'keywords': 'At most 20 keywords are allowed.'})
            attrs['keywords'] = list(dict.fromkeys(keywords))
        return attrs

    @staticmethod
    def _set_keywords(advertisement, values):
        keywords = [AdvKeyword.objects.get_or_create(name=value)[0] for value in values]
        advertisement.keywords.set(keywords)

    @staticmethod
    def _set_images(advertisement, images):
        advertisement.images.all().delete()
        for image in images:
            AdvImage.objects.create(advertise=advertisement, image=image)

    def create(self, validated_data):
        keyword_values = validated_data.pop('keywords', [])
        images = validated_data.pop('images', [])
        product = validated_data.pop('product', None)
        if product:
            for field in ('type', 'name', 'description', 'price', 'category'):
                validated_data.pop(field, None)
            validated_data.update(
                product=product,
                type=product.type,
                name=product.name,
                description=product.description or '',
                price=product.main_price,
                category=product.sub_category.category,
            )
        advertisement = Advertisement.objects.create(**validated_data)
        self._set_keywords(advertisement, keyword_values)
        if images:
            self._set_images(advertisement, images)
        return advertisement

    def update(self, instance, validated_data):
        keyword_values = validated_data.pop('keywords', None)
        images = validated_data.pop('images', None)
        validated_data.pop('product', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if keyword_values is not None:
            self._set_keywords(instance, keyword_values)
        if images is not None:
            self._set_images(instance, images)
        return instance


class AdvertiseListSerializer(serializers.ModelSerializer):
    category = serializers.SerializerMethodField()
    updated_at = serializers.SerializerMethodField()
    images = AdvertiseImageSerializer(many=True, read_only=True)

    class Meta:
        model = Advertisement
        fields = ['id', 'name', 'category', 'price', 'updated_at', 'images']

    @extend_schema_field(serializers.CharField())
    def get_updated_at(self, obj) -> str:
        jalali_date = jdatetime.fromgregorian(date=obj.updated_at)
        return jalali_date.strftime('%Y/%m/%d %H:%M')

    @extend_schema_field(serializers.DictField())
    def get_category(self, obj) -> Dict[str, Any]:
        if not obj.category:
            return {}
        return {'id': obj.category.id, 'title': obj.category.title}
