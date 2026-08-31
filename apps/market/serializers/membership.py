from rest_framework import serializers

from apps.market.models import MarketMembership


class MarketMembershipInputSerializer(serializers.Serializer):
    mobile_number = serializers.CharField(max_length=15, trim_whitespace=True)
    role = serializers.ChoiceField(choices=MarketMembership.ROLE_CHOICES)
    permissions = serializers.ListField(
        child=serializers.ChoiceField(choices=('products', 'orders', 'messages', 'profile', 'sms')),
        required=False,
        default=list,
    )


class MarketMembershipUpdateSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=MarketMembership.ROLE_CHOICES)
    permissions = serializers.ListField(
        child=serializers.ChoiceField(choices=('products', 'orders', 'messages', 'profile', 'sms')),
        required=False,
    )
    is_active = serializers.BooleanField(required=False)


class MarketMembershipSerializer(serializers.ModelSerializer):
    user_id = serializers.UUIDField(source='user.id', read_only=True)

    class Meta:
        model = MarketMembership
        fields = (
            'id', 'market', 'user_id', 'role', 'permissions', 'status',
            'is_active', 'review_note', 'owner_approved_at', 'admin_approved_at', 'created_at',
        )
        read_only_fields = fields
