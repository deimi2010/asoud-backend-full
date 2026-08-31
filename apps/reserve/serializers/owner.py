from jdatetime import datetime as jdatetime
from rest_framework import serializers

from apps.market.serializers.user_serializers import MarketListSerializer
from apps.product.models import Product
from apps.reserve.models import (
    DayOff,
    Reservation,
    ReserveTime,
    Service,
    Specialist,
    SpecialistTimeOff,
)
from apps.users.serializers import UserSerializer


class ServiceSerializer(serializers.ModelSerializer):
    market = MarketListSerializer(read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_price = serializers.DecimalField(
        source='product.main_price', max_digits=14, decimal_places=3, read_only=True,
    )

    class Meta:
        model = Service
        fields = [
            'id', 'market', 'product', 'product_name', 'product_price', 'name',
            'duration_minutes', 'buffer_minutes', 'capacity', 'payment_mode',
            'fixed_fee', 'deposit_percentage', 'requires_owner_confirmation',
            'max_advance_days', 'cancellation_hours', 'is_active',
        ]
        read_only_fields = fields


class AppointmentProductSerializer(serializers.ModelSerializer):
    configured_service = serializers.UUIDField(
        source='appointment_service.id', read_only=True, allow_null=True,
    )

    class Meta:
        model = Product
        fields = ('id', 'name', 'main_price', 'status', 'configured_service')
        read_only_fields = fields


class ServiceCreateSerializer(serializers.ModelSerializer):
    market = serializers.UUIDField()
    product = serializers.UUIDField(required=False, allow_null=True)
    name = serializers.CharField(max_length=32, required=False)

    class Meta:
        model = Service
        fields = [
            'market', 'product', 'name', 'duration_minutes', 'buffer_minutes', 'capacity',
            'payment_mode', 'fixed_fee', 'deposit_percentage',
            'requires_owner_confirmation', 'max_advance_days',
            'cancellation_hours', 'is_active',
        ]

    def validate(self, attrs):
        if not attrs.get('product') and not str(attrs.get('name', '')).strip():
            raise serializers.ValidationError({'product': 'Select a service product.'})
        mode = attrs.get('payment_mode', Service.FREE)
        if mode == Service.FIXED and attrs.get('fixed_fee', 0) <= 0:
            raise serializers.ValidationError({'fixed_fee': 'A positive fixed fee is required.'})
        if mode == Service.DEPOSIT_PERCENT and not 1 <= attrs.get('deposit_percentage', 0) <= 100:
            raise serializers.ValidationError({'deposit_percentage': 'Use a percentage from 1 to 100.'})
        return attrs


class ServiceUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = [
            'duration_minutes', 'buffer_minutes', 'capacity', 'payment_mode',
            'fixed_fee', 'deposit_percentage', 'requires_owner_confirmation',
            'max_advance_days', 'cancellation_hours', 'is_active',
        ]

    def validate(self, attrs):
        if 'market' in self.initial_data or 'product' in self.initial_data:
            raise serializers.ValidationError({'product': 'Market and product are read-only.'})
        mode = attrs.get('payment_mode', self.instance.payment_mode)
        fixed_fee = attrs.get('fixed_fee', self.instance.fixed_fee)
        percentage = attrs.get('deposit_percentage', self.instance.deposit_percentage)
        if mode == Service.FIXED and fixed_fee <= 0:
            raise serializers.ValidationError({'fixed_fee': 'A positive fixed fee is required.'})
        if mode == Service.DEPOSIT_PERCENT and not 1 <= percentage <= 100:
            raise serializers.ValidationError({'deposit_percentage': 'Use a percentage from 1 to 100.'})
        return attrs


class SpecialistSerializer(serializers.ModelSerializer):
    services = ServiceSerializer(many=True, read_only=True)

    class Meta:
        model = Specialist
        fields = ['id', 'market', 'account', 'user', 'services', 'field', 'is_active']
        read_only_fields = fields


class SpecialistCreateSerializer(serializers.ModelSerializer):
    services = serializers.ListField(
        child=serializers.UUIDField(),
        allow_empty=False,
    )

    class Meta:
        model = Specialist
        fields = ['market', 'account', 'user', 'services', 'field', 'is_active']

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
    market = serializers.UUIDField(required=False)


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
        fields = ['id', 'market', 'date', 'date_jalali']
        read_only_fields = fields

    def get_date_jalali(self, obj) -> str:
        jalali_date = jdatetime.fromgregorian(date=obj.date)
        return jalali_date.strftime('%Y/%m/%d')


class DayOffCreateSerializer(serializers.ModelSerializer):
    market = serializers.UUIDField()

    class Meta:
        model = DayOff
        fields = ['market', 'date']
        # The endpoint intentionally uses get_or_create so retrying the same
        # request is idempotent instead of failing model-level uniqueness here.
        validators = []

    def validate_date(self, value):
        from django.utils import timezone
        if value < timezone.localdate():
            raise serializers.ValidationError('Past dates cannot be closed.')
        return value


class SpecialistTimeOffSerializer(serializers.ModelSerializer):
    class Meta:
        model = SpecialistTimeOff
        fields = ('id', 'specialist', 'date', 'start', 'end', 'reason')
        read_only_fields = ('id',)

    def validate(self, attrs):
        start, end = attrs.get('start'), attrs.get('end')
        if (start is None) != (end is None):
            raise serializers.ValidationError('Start and end must both be set for a partial day.')
        if start is not None and end <= start:
            raise serializers.ValidationError('End time must be after start time.')
        return attrs


class ReservationSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    reserve = ReserveTimeSerializer(read_only=True)
    specialist_name = serializers.CharField(source='specialist.user', read_only=True)

    class Meta:
        model = Reservation
        fields = [
            'id', 'tracking_code', 'user', 'reserve', 'service', 'specialist',
            'specialist_name',
            'scheduled_start', 'scheduled_end', 'status', 'is_paid',
            'service_name_snapshot', 'price_snapshot', 'payment_mode_snapshot',
            'amount_due', 'hold_expires_at', 'confirmed_at', 'cancelled_at',
            'cancellation_reason', 'created_at',
        ]
        read_only_fields = fields


class ReservationStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=(
        Reservation.CONFIRMED,
        Reservation.COMPLETED,
        Reservation.CANCELLED,
        Reservation.NO_SHOW,
    ))
    reason = serializers.CharField(max_length=240, required=False, allow_blank=True)
