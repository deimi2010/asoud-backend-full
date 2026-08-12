from jdatetime import datetime as jdatetime
from rest_framework import serializers

from apps.market.serializers.user_serializers import MarketListSerializer
from apps.reserve.models import DayOff, Reservation, ReserveTime, Service, Specialist
from apps.users.serializers import UserSerializer


class ServiceSerializer(serializers.ModelSerializer):
    market = MarketListSerializer(read_only=True)

    class Meta:
        model = Service
        fields = ['id', 'market', 'name']
        read_only_fields = fields


class ServiceCreateSerializer(serializers.ModelSerializer):
    market = serializers.UUIDField()

    class Meta:
        model = Service
        fields = ['market', 'name']

    def validate_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError('Name cannot be empty.')
        return value


class ServiceUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = ['name']

    def validate_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError('Name cannot be empty.')
        return value

    def validate(self, attrs):
        if 'market' in self.initial_data:
            raise serializers.ValidationError({'market': 'This field is read-only.'})
        return attrs


class SpecialistSerializer(serializers.ModelSerializer):
    services = ServiceSerializer(many=True, read_only=True)

    class Meta:
        model = Specialist
        fields = ['id', 'user', 'services', 'field']
        read_only_fields = fields


class SpecialistCreateSerializer(serializers.ModelSerializer):
    services = serializers.ListField(
        child=serializers.UUIDField(),
        allow_empty=False,
    )

    class Meta:
        model = Specialist
        fields = ['user', 'services', 'field']

    def validate_services(self, value):
        if len(value) != len(set(value)):
            raise serializers.ValidationError('Services must be unique.')
        return value


class SpecialistUpdateSerializer(SpecialistCreateSerializer):
    services = serializers.ListField(
        child=serializers.UUIDField(),
        allow_empty=False,
        required=False,
    )
    user = serializers.CharField(required=False)


class ReserveTimeSerializer(serializers.ModelSerializer):
    service = ServiceSerializer(read_only=True)

    class Meta:
        model = ReserveTime
        fields = ['id', 'service', 'day', 'start', 'end']
        read_only_fields = fields


class ReserveTimeCreateSerializer(serializers.ModelSerializer):
    service = serializers.UUIDField()

    class Meta:
        model = ReserveTime
        fields = ['service', 'day', 'start', 'end']

    def validate(self, attrs):
        end = attrs.get('end')
        if end is not None and end <= attrs['start']:
            raise serializers.ValidationError('End time must be after start time.')
        return attrs


class ReserveTimeUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReserveTime
        fields = ['day', 'start', 'end']

    def validate(self, attrs):
        if 'service' in self.initial_data:
            raise serializers.ValidationError({'service': 'This field is read-only.'})
        start = attrs.get('start', self.instance.start)
        end = attrs.get('end', self.instance.end)
        if end is not None and end <= start:
            raise serializers.ValidationError('End time must be after start time.')
        return attrs


class DayOffSerializer(serializers.ModelSerializer):
    market = MarketListSerializer(read_only=True)
    date_jalali = serializers.SerializerMethodField()

    class Meta:
        model = DayOff
        fields = ['id', 'market', 'date_jalali']
        read_only_fields = fields

    def get_date_jalali(self, obj) -> str:
        jalali_date = jdatetime.fromgregorian(date=obj.date)
        return jalali_date.strftime('%Y/%m/%d')


class DayOffCreateSerializer(serializers.ModelSerializer):
    market = serializers.UUIDField()

    class Meta:
        model = DayOff
        fields = ['market', 'date']


class ReservationSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    reserve = ReserveTimeSerializer(read_only=True)

    class Meta:
        model = Reservation
        fields = ['id', 'user', 'reserve', 'specialist', 'is_paid']
        read_only_fields = fields
