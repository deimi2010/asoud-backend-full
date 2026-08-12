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

    class Meta:
        model = Discount
        fields = [
            'id', 
            'code', 
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
    class Meta:
        model = Discount
        fields = ['id', 'code', 'percentage', 'expiry']

class DiscountDetailSerializer(DiscountCreateSerializer):
    pass

