from rest_framework import serializers

from apps.market.models import MarketMembership


class MarketMembershipInputSerializer(serializers.Serializer):
    mobile_number = serializers.CharField(max_length=15, trim_whitespace=True)
    role = serializers.ChoiceField(choices=MarketMembership.ROLE_CHOICES)


class MarketMembershipUpdateSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=MarketMembership.ROLE_CHOICES)


class MarketMembershipSerializer(serializers.ModelSerializer):
    user_id = serializers.UUIDField(source='user.id', read_only=True)

    class Meta:
        model = MarketMembership
        fields = ('id', 'market', 'user_id', 'role', 'is_active', 'created_at')
        read_only_fields = fields
