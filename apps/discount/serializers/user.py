from rest_framework import serializers
from apps.discount.models import Discount
from django.contrib.contenttypes.models import ContentType


class DiscountValidateSerializer(serializers.Serializer):
    code = serializers.CharField()
    content_type = serializers.SlugRelatedField(
        queryset=ContentType.objects.filter(
            model__in=['product', 'market']
        ),
        slug_field='model', 
    )
    object_id = serializers.UUIDField()

class DiscountValidateResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Discount
        fields = ['id', 'code', 'percentage', 'expiry', 'position']