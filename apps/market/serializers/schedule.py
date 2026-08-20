from rest_framework import serializers

from apps.market.models import MarketSchedule


class MarketScheduleSerializer(serializers.ModelSerializer):
    market = serializers.UUIDField(source='market_id', read_only=True)
    day = serializers.SerializerMethodField()
    start = serializers.TimeField(source='start_time', read_only=True)
    end = serializers.TimeField(source='end_time', read_only=True)

    class Meta:
        model = MarketSchedule
        fields = ['id', 'market', 'day', 'start', 'end']
        read_only_fields = fields

    def get_day(self, obj) -> str:
        # Flutter's established contract numbers Saturday through Friday as 1..7.
        return str(obj.day_of_week + 1)


class MarketScheduleInputSerializer(serializers.Serializer):
    market = serializers.UUIDField()
    day = serializers.IntegerField(min_value=1, max_value=7)
    start = serializers.TimeField()
    end = serializers.TimeField()

    def validate(self, attrs):
        if attrs['end'] <= attrs['start']:
            raise serializers.ValidationError('End time must be after start time.')
        return attrs


class MarketScheduleUpdateSerializer(serializers.Serializer):
    day = serializers.IntegerField(min_value=1, max_value=7, required=False)
    start = serializers.TimeField(required=False)
    end = serializers.TimeField(required=False)

    def validate(self, attrs):
        schedule = self.context['schedule']
        start = attrs.get('start', schedule.start_time)
        end = attrs.get('end', schedule.end_time)
        if end <= start:
            raise serializers.ValidationError('End time must be after start time.')
        return attrs


class MarketScheduleListQuerySerializer(serializers.Serializer):
    market = serializers.UUIDField(required=False)


class MarketScheduleReplaceItemSerializer(serializers.Serializer):
    day = serializers.IntegerField(min_value=1, max_value=7)
    interval_index = serializers.IntegerField(min_value=1, max_value=2)
    start = serializers.TimeField()
    end = serializers.TimeField()

    def validate(self, attrs):
        if attrs['end'] <= attrs['start']:
            raise serializers.ValidationError('End time must be after start time.')
        return attrs


class MarketScheduleReplaceSerializer(serializers.Serializer):
    market = serializers.UUIDField()
    schedules = MarketScheduleReplaceItemSerializer(many=True)

    def validate_schedules(self, schedules):
        slots = set()
        by_day = {}
        for item in schedules:
            slot = (item['day'], item['interval_index'])
            if slot in slots:
                raise serializers.ValidationError('Duplicate day interval index.')
            slots.add(slot)
            by_day.setdefault(item['day'], []).append(item)
        for intervals in by_day.values():
            ordered = sorted(intervals, key=lambda item: item['start'])
            for previous, current in zip(ordered, ordered[1:]):
                if current['start'] < previous['end']:
                    raise serializers.ValidationError(
                        'Working intervals cannot overlap.'
                    )
        return schedules


class MarketScheduleEnvelopeSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    code = serializers.IntegerField()
    data = MarketScheduleSerializer()


class MarketScheduleListEnvelopeSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    code = serializers.IntegerField()
    data = MarketScheduleSerializer(many=True)
