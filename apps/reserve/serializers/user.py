from rest_framework import serializers

from apps.reserve.models import Specialist
from apps.reserve.serializers.owner import (
    DayOffSerializer,
    ReserveTimeSerializer,
    ServiceSerializer,
)


class ServiceListSerializer(ServiceSerializer):
    pass


class SpecialistListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Specialist
        fields = ['id', 'user', 'field']
        read_only_fields = fields


class ReserveTimeListSerializer(ReserveTimeSerializer):
    pass


class DayoffListSerializer(DayOffSerializer):
    pass


class ReservationCreateSerializer(serializers.Serializer):
    reserve = serializers.UUIDField(required=False)
    service = serializers.UUIDField(required=False)
    specialist = serializers.PrimaryKeyRelatedField(queryset=Specialist.objects.all())
    scheduled_start = serializers.DateTimeField(required=False)

    def validate(self, attrs):
        if 'is_paid' in self.initial_data:
            raise serializers.ValidationError({'is_paid': 'This field is read-only.'})
        modern = attrs.get('service') and attrs.get('scheduled_start')
        if not modern and not attrs.get('reserve'):
            raise serializers.ValidationError(
                {'service': 'Service and scheduled_start are required.'}
            )
        return attrs


class AvailabilityQuerySerializer(serializers.Serializer):
    service = serializers.UUIDField()
    specialist = serializers.UUIDField()
    date = serializers.DateField()


class ReservationRescheduleSerializer(serializers.Serializer):
    scheduled_start = serializers.DateTimeField()


class ReservationCancelSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=240, required=False, allow_blank=True)


class ReservationListQuerySerializer(serializers.Serializer):
    market = serializers.UUIDField(required=False)
