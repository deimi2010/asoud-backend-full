from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.users.models import User


class ReferralCreateSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=15, trim_whitespace=True)

    def validate_code(self, value):
        if not value:
            raise serializers.ValidationError('Referral code cannot be empty.')
        return value


class ReferredUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id']
        read_only_fields = fields


class ReferralListSerializer(serializers.ModelSerializer):
    # Keep the historical misspelling until a versioned API can rename it.
    referrees = serializers.SerializerMethodField()
    referral_count = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'referral_count', 'referrees']
        read_only_fields = fields

    @extend_schema_field(ReferredUserSerializer(many=True))
    def get_referrees(self, obj):
        referrals = obj.referrals_made.all()
        return ReferredUserSerializer(
            [referral.referred_user for referral in referrals],
            many=True,
        ).data

    def get_referral_count(self, obj) -> int:
        return len(obj.referrals_made.all())


class ReferralCreatedDataSerializer(serializers.Serializer):
    id = serializers.UUIDField()


class ReferralCreatedEnvelopeSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    code = serializers.IntegerField()
    data = ReferralCreatedDataSerializer()


class ReferralListEnvelopeSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    code = serializers.IntegerField()
    data = ReferralListSerializer()
