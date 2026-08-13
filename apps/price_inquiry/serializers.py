from rest_framework import serializers
from apps.price_inquiry.models import (
    Inquiry,
    InquiryImage,
    InquiryAnswer,
    InquiryAnswerImage
)
from jdatetime import datetime as jdatetime
from django.utils import timezone


class InquiryImageSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(read_only=True)

    class Meta:
        model = InquiryImage
        fields = [
            'id',
            'image'
        ]

class InquiryImageListSerializer(serializers.Serializer):
    images = serializers.ListField(child=serializers.ImageField())
    
    def create(self, validated_data):
        # inquiry = self.context.get('inquiry')
        inquiry = validated_data.pop('inquiry', None)

        if not inquiry:
            raise ValueError("Inquiry is required")
        
        images = []

        for img in validated_data['images']:
            image = InquiryImage.objects.create(
                inquiry=inquiry,
                image=img
            )
            images.append(image)
        
        return images
    
class InquirySerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(read_only=True)
    user = serializers.SerializerMethodField()
    expiry = serializers.SerializerMethodField()
    images = InquiryImageSerializer(many=True, required=False)
    
    class Meta:
        model = Inquiry
        fields = [
            'id',
            'user',
            'type',
            'name',
            'technical_detail',
            'amount',
            'unit',
            'expiry',
            'send',
            'images'
        ]

    def get_expiry(self, obj) -> str:
        _date = obj.expiry
        jalali_date = jdatetime.fromgregorian(date=_date)
        return jalali_date.strftime("%Y/%m/%d %H:%M")

    def get_user(self, obj) -> dict:
        return {'id': str(obj.user_id)}

class InquiryCreateSerializer(serializers.ModelSerializer):
    technical_detail = serializers.CharField(required=False)
    amount = serializers.CharField(required=False)
    unit = serializers.CharField(required=False)
    expiry = serializers.DateTimeField()

    class Meta:
        model = Inquiry
        fields = [
            'type',
            'name',
            'technical_detail',
            'amount',
            'unit',
            'expiry',
        ]

    def validate_type(self, value):
        if value not in ['good', 'service']:
            raise serializers.ValidationError("type must be either good or service")
        return value

    def validate_amount(self, value):
        if len(value) > 10:
            raise serializers.ValidationError("amount must be less than 10 characters long.")
        return value

    def validate_unit(self, value):
        if len(value) > 10:
            raise serializers.ValidationError("unit must be less than 10 characters long.")
        return value

    def validate_expiry(self, value):
        if value <= timezone.now():
            raise serializers.ValidationError("expiry must be in the future")
        return value


class InquiryUpdateSerializer(InquiryCreateSerializer):
    pass


class InquirySendSetSerializer(serializers.Serializer):
    send = serializers.JSONField()

    def validate_send(self, value):
        if value is True or value == Inquiry.CHAT:
            return Inquiry.CHAT
        if value == Inquiry.SMS:
            raise serializers.ValidationError("SMS inquiry delivery is unavailable")
        raise serializers.ValidationError("send must be true or chat")
    
class InquiryExpireSetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Inquiry
        fields = [
            'expiry'
        ]

    def validate_expiry(self, value):
        if value <= timezone.now():
            raise serializers.ValidationError("expiry must be in the future")
        return value

class InquiryAnswerImageSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(read_only=True)
    class Meta:
        model = InquiryAnswerImage
        fields = [
            'id',
            'image'
        ]

class InquiryAnswerSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(read_only=True)
    inquiry = InquirySerializer(read_only=True)
    user = serializers.SerializerMethodField()
    fee = serializers.CharField(required=False)
    images = InquiryAnswerImageSerializer(many=True)

    class Meta:
        model = InquiryAnswer
        fields = [
            'id',
            'inquiry',
            'user',
            'detail',
            'total',
            'fee',
            'images',
        ]

    def get_user(self, obj) -> dict:
        return {'id': str(obj.user_id)}

class InquiryAnswerCreateSerializer(InquiryAnswerSerializer):
    inquiry = serializers.UUIDField()
    images = serializers.ListField(child=serializers.ImageField(), required=False)

    def create(self, validated_data):
        inquiry = validated_data.pop('inquiry')
        user = validated_data.pop('user')
        images = validated_data.pop('images', None)
        
        answer = InquiryAnswer.objects.create(
            **validated_data,
            inquiry=inquiry,
            user=user
        )

        for image in images or []:
            _ = InquiryAnswerImage.objects.create(
                answer=answer,
                image=image
            )
        
        return answer
