import json
from rest_framework import serializers
from apps.sms.models import (
    Line, 
    Template,
    BulkSms,
    PatternSms
)

class LineSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(read_only=True)
    is_active = serializers.BooleanField(required=False)
    
    class Meta:
        model = Line
        fields = '__all__'

class TemplateSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(read_only=True)
    is_active = serializers.BooleanField(required=False)

    class Meta:
        model = Template
        fields = '__all__'

class BulkUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = BulkSms
        fields = ['status']

class BulkSerializer(serializers.ModelSerializer):
    class Meta:
        model = BulkSms
        fields = '__all__'


class PatternSerializer(serializers.ModelSerializer):
    class Meta:
        model = PatternSms
        fields = '__all__'
