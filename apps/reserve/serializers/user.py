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
    reserve = serializers.UUIDField()
    specialist = serializers.PrimaryKeyRelatedField(queryset=Specialist.objects.all())

    def validate(self, attrs):
        if 'is_paid' in self.initial_data:
            raise serializers.ValidationError({'is_paid': 'This field is read-only.'})
        return attrs
