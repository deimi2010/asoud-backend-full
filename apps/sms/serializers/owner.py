from urllib.parse import urlparse

from rest_framework import serializers

from apps.sms.models import BulkSms, Contact, Line, SmsCampaign, SmsRecipient, SmsTariff, Template


def normalize_mobile(value):
    value = str(value or '').strip().replace(' ', '').replace('-', '')
    if value.startswith('+98'):
        value = f'0{value[3:]}'
    elif value.startswith('98') and len(value) == 12:
        value = f'0{value[2:]}'
    if len(value) != 11 or not value.isascii() or not value.isdecimal() or not value.startswith('09'):
        raise serializers.ValidationError('شماره همراه باید ۱۱ رقم و با 09 شروع شود.')
    return value


class LineListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Line
        fields = ('id', 'number', 'estimated_cost')


class BulkSmsCreateSerializer(serializers.ModelSerializer):
    """Read-only billing/provider fields retained for legacy client safety."""

    class Meta:
        model = BulkSms
        exclude = ('user', 'message_ids')
        read_only_fields = ('cost', 'actual_cost', 'status', 'packId')


class TemplateListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Template
        fields = (
            'id', 'template_id', 'title', 'category', 'content', 'variables',
            'approval_status', 'is_public', 'review_note', 'is_active',
        )
        read_only_fields = fields


class TemplateCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Template
        fields = ('id', 'title', 'category', 'content')
        read_only_fields = ('id',)

    def create(self, validated_data):
        return Template.objects.create(
            owner=self.context['request'].user,
            variables=[], estimated_cost=0, approval_status='pending',
            is_public=False, is_active=True, **validated_data,
        )


class SmsContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = ('id', 'name', 'mobile_number', 'source', 'has_consent')
        read_only_fields = ('id',)

    def validate_mobile_number(self, value):
        return normalize_mobile(value)


class RecipientInputSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=64, required=False, allow_blank=True, default='')
    mobile_number = serializers.CharField(max_length=15)

    def validate_mobile_number(self, value):
        return normalize_mobile(value)


class CampaignCreateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=100)
    market = serializers.UUIDField(required=False, allow_null=True)
    template = serializers.UUIDField(required=False, allow_null=True)
    line = serializers.UUIDField()
    message = serializers.CharField(max_length=2000)
    link = serializers.URLField(max_length=500, required=False, allow_blank=True, default='')
    recipients = RecipientInputSerializer(many=True, min_length=1, max_length=10000)
    scheduled_at = serializers.DateTimeField(required=False, allow_null=True)

    def validate_link(self, value):
        if not value:
            return value
        parsed = urlparse(value)
        hostname = (parsed.hostname or '').lower().rstrip('.')
        if parsed.scheme != 'https' or not (hostname == 'asoud.ir' or hostname.endswith('.asoud.ir')):
            raise serializers.ValidationError('لینک باید HTTPS و متعلق به asoud.ir یا زیردامنه آن باشد.')
        return value

    def validate_recipients(self, value):
        return list({item['mobile_number']: item for item in value}.values())


class SmsRecipientSerializer(serializers.ModelSerializer):
    class Meta:
        model = SmsRecipient
        fields = ('id', 'name', 'mobile_number', 'status', 'actual_cost', 'error_message')


class SmsCampaignSerializer(serializers.ModelSerializer):
    recipients = SmsRecipientSerializer(many=True, read_only=True)
    template_title = serializers.CharField(source='template.title', read_only=True, allow_null=True)

    class Meta:
        model = SmsCampaign
        fields = (
            'id', 'title', 'market', 'template', 'template_title', 'message', 'link',
            'status', 'recipient_count', 'segment_count', 'estimated_cost',
            'reserved_cost', 'actual_cost', 'scheduled_at', 'sent_at',
            'failure_reason', 'created_at', 'recipients',
        )


class SmsTariffSerializer(serializers.ModelSerializer):
    class Meta:
        model = SmsTariff
        fields = ('id', 'title', 'price_per_segment', 'effective_from')
