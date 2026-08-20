from rest_framework import serializers
from apps.discount.models import Discount
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone


class DiscountCreateSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(read_only=True)
    code = serializers.CharField(read_only=True)
    content_type = serializers.SlugRelatedField(
        queryset=ContentType.objects.filter(
            model__in=['product', 'market']
        ),
        slug_field='model', 
    )
    object_id = serializers.UUIDField()
    expiry = serializers.DateTimeField(required=False)
    limitation = serializers.IntegerField(required=False)
    position = serializers.CharField(required=False)
    client_request_id = serializers.CharField(
        required=False,
        allow_blank=False,
        max_length=64,
        write_only=True,
    )

    class Meta:
        model = Discount
        fields = [
            'id', 
            'code', 
            'title',
            'description',
            'client_request_id',
            'content_type',
            'object_id',
            'percentage',
            'expiry',
            'limitation',
            'users',
            'position',
            'created_at'
        ]
    
    def validate(self, data):
        """
        Validate that the object_id corresponds to a valid Product or Market.
        """
        content_type = data['content_type']
        object_id = data['object_id']

        # Get the model class from the content type
        model_class = content_type.model_class()

        # Check if the object exists
        if not model_class.objects.filter(id=object_id).exists():
            raise serializers.ValidationError(
                f"No {content_type.model} found with id {object_id}."
            )

        expiry = data.get('expiry')
        if expiry and expiry <= timezone.now():
            raise serializers.ValidationError({'expiry': 'Expiry must be in the future.'})

        return data

    def validate_percentage(self, value):
        if not 1 <= value <= 100:
            raise serializers.ValidationError('Percentage must be between 1 and 100.')
        return value

    def validate_limitation(self, value):
        if value < 0:
            raise serializers.ValidationError('Limitation cannot be negative.')
        return value

    def validate_users(self, value):
        if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
            raise serializers.ValidationError('Users must be a list of mobile numbers or user IDs.')
        return list(dict.fromkeys(value))
    
class DiscountListSerializer(serializers.ModelSerializer):
    status = serializers.SerializerMethodField()
    remaining = serializers.SerializerMethodField()
    store_name = serializers.SerializerMethodField()
    store_business_id = serializers.SerializerMethodField()

    class Meta:
        model = Discount
        fields = [
            'id',
            'title',
            'description',
            'code',
            'percentage',
            'limitation',
            'consumed',
            'reserved',
            'remaining',
            'expiry',
            'is_active',
            'status',
            'store_name',
            'store_business_id',
            'created_at',
        ]

    def get_status(self, obj):
        if not obj.is_active:
            return 'inactive'
        if obj.expiry and obj.expiry < timezone.now():
            return 'expired'
        if obj.limitation and obj.consumed + obj.reserved >= obj.limitation:
            return 'full'
        return 'active'

    def get_remaining(self, obj):
        if obj.limitation == 0:
            return None
        return max(obj.limitation - obj.consumed - obj.reserved, 0)

    def _market(self, obj):
        target = obj.content_object
        return target if obj.content_type.model == 'market' else target.market

    def get_store_name(self, obj):
        return self._market(obj).name

    def get_store_business_id(self, obj):
        return self._market(obj).business_id

class DiscountDetailSerializer(DiscountCreateSerializer):
    pass
