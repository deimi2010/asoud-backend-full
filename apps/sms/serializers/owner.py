import json
from rest_framework import serializers
from apps.sms.models import (
    Line, 
    Template,
    BulkSms,
    PatternSms
)


class LineListSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(read_only=True)
    
    class Meta:
        model = Line
        fields = ['id', 'number', 'estimated_cost']

class TemplateListSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(read_only=True)

    class Meta:
        model = Template
        fields = ['id', 'template_id', 'content', 'variables']

class BulkSmsCreateSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(read_only=True)
    cost = serializers.FloatField(read_only=True)
    actual_cost = serializers.FloatField(read_only=True)
    status = serializers.CharField(read_only=True)
    packId = serializers.CharField(read_only=True)
    
    class Meta:
        model = BulkSms
        exclude = ['user', 'message_ids']
    
    def to_payload(self, validated_data: dict):
        """Convert validated data to SMS API payload format"""
        return {
            "lineNumber": validated_data['line'].number,
            "messageText": validated_data['content'],
            "mobiles": validated_data['to']
        }

class BulkSmsViewSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(read_only=True)
    class Meta:
        model = BulkSms
        fields = [
            'id',
            'line', 
            'content',
            'to'
        ]

class PatternSmsCreateSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(read_only=True)
    template = serializers.UUIDField()
    cost = serializers.FloatField(read_only=True)
    actual_cost = serializers.FloatField(read_only=True)
    status = serializers.CharField(read_only=True)
    variables = serializers.JSONField(required=True)

    class Meta:
        model = PatternSms
        exclude = ['user', 'message_id']

    def to_payload(self, validated_data: dict):
        try:
            template = Template.objects.get(id=validated_data['template'])
        except Template.DoesNotExist:
            raise Exception('Template Not Found')
        
        # check variables required for the template
        variables = template.variables
        needed_variables = list( variables.keys() )
        input_variables = [v['name'] for v in validated_data['variables']]

        if len(needed_variables) != len(input_variables):
            raise Exception('Extra/Less Variables Received')
        
        errors = {}
        for v in needed_variables:
            if v not in input_variables:
                errors['v'] = "Not Provided"

        if errors:
            raise Exception(json.dumps(errors))
        
        # for v in validated_data['variables']:
        #     v['name'] = v['name'].upper()
        
        return [
            {
                "Mobile": mobile,
                "TemplateId": int(template.template_id),
                "Parameters": validated_data['variables']
            }  
            for mobile in validated_data['to']
        ]

class PatternSmsViewSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(read_only=True)
    template = serializers.SerializerMethodField()
    
    class Meta:
        model = PatternSms
        fields = [
            'id',
            'template', 
            'to',
            'variables',
            'cost',
            'actual_cost',
            'status',
            'created_at'
        ]
    
    def get_template(self, obj):
        if obj.template:
            return {
                'id': obj.template.id,
                'template_id': obj.template.template_id,
                'content': obj.template.content
            }
        return None


class SmsListSerializer(serializers.ModelSerializer):
    sms_type = serializers.SerializerMethodField()
    
    class Meta:
        model = BulkSms
        fields = [
            'id',
            'line',
            'content',
            'to',
            'cost',
            'actual_cost', 
            'status',
            'sms_type',
            'created_at'
        ]
    
    def get_sms_type(self, obj):
        return 'bulk'


class SmsHistorySerializer(serializers.ModelSerializer):
    """Combined serializer for SMS history including both bulk and pattern SMS"""
    sms_type = serializers.CharField(read_only=True)
    content_preview = serializers.SerializerMethodField()
    recipient_count = serializers.SerializerMethodField()
    
    class Meta:
        model = BulkSms  # Base model, will be extended
        fields = [
            'id',
            'sms_type',
            'content_preview',
            'recipient_count',
            'cost',
            'actual_cost',
            'status',
            'created_at'
        ]
    
    def get_content_preview(self, obj):
        """Get a preview of SMS content"""
        if hasattr(obj, 'content') and obj.content:
            return obj.content[:100] + "..." if len(obj.content) > 100 else obj.content
        elif hasattr(obj, 'template') and obj.template:
            return obj.template.content[:100] + "..." if len(obj.template.content) > 100 else obj.template.content
        return "No content"
    
    def get_recipient_count(self, obj):
        """Get count of recipients"""
        if hasattr(obj, 'to') and obj.to:
            return len(obj.to) if isinstance(obj.to, list) else 1
        return 0
