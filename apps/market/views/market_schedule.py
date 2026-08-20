from django.db import transaction
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import permissions, serializers, status, views
from rest_framework.response import Response

from apps.market.models import Market, MarketSchedule
from apps.market.serializers.schedule import (
    MarketScheduleInputSerializer,
    MarketScheduleEnvelopeSerializer,
    MarketScheduleListEnvelopeSerializer,
    MarketScheduleListQuerySerializer,
    MarketScheduleSerializer,
    MarketScheduleUpdateSerializer,
    MarketScheduleReplaceSerializer,
)
from utils.response import ApiResponse


def _overlapping_schedules(*, market, day_of_week, start_time, end_time, exclude=None):
    queryset = MarketSchedule.objects.filter(
        market=market,
        day_of_week=day_of_week,
        start_time__lt=end_time,
        end_time__gt=start_time,
    )
    if exclude is not None:
        queryset = queryset.exclude(id=exclude)
    return queryset


def _schedule_response(schedule, *, code=status.HTTP_200_OK):
    return Response(
        ApiResponse(
            success=True,
            code=code,
            data=MarketScheduleSerializer(schedule).data,
        ),
        status=code,
    )


def _lock_owned_schedule(*, schedule_id, user):
    ownership = {} if user.is_staff else {'market__user': user}
    candidate = get_object_or_404(
        MarketSchedule.objects.only('market_id'),
        id=schedule_id,
        **ownership,
    )
    market_ownership = {} if user.is_staff else {'user': user}
    market = get_object_or_404(
        Market.objects.select_for_update(),
        id=candidate.market_id,
        **market_ownership,
    )
    return get_object_or_404(
        MarketSchedule.objects.select_for_update(),
        id=schedule_id,
        market=market,
    )


class MarketScheduleAPIView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        request=MarketScheduleInputSerializer,
        responses={
            200: MarketScheduleEnvelopeSerializer,
            201: MarketScheduleEnvelopeSerializer,
            400: OpenApiResponse(description='Invalid or overlapping interval.'),
            404: OpenApiResponse(description='Owned Market not found.'),
        },
    )
    @transaction.atomic
    def post(self, request):
        serializer = MarketScheduleInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        markets = Market.objects.select_for_update()
        if not request.user.is_staff:
            markets = markets.filter(user=request.user)
        market = get_object_or_404(markets, id=data['market'])
        day_of_week = data['day'] - 1
        exact = MarketSchedule.objects.filter(
            market=market,
            day_of_week=day_of_week,
            start_time=data['start'],
            end_time=data['end'],
        ).first()
        if exact is not None:
            return _schedule_response(exact)
        if _overlapping_schedules(
            market=market,
            day_of_week=day_of_week,
            start_time=data['start'],
            end_time=data['end'],
        ).exists():
            raise serializers.ValidationError(
                {'non_field_errors': ['Schedule overlaps an existing interval.']}
            )
        schedule = MarketSchedule.objects.create(
            market=market,
            day_of_week=day_of_week,
            start_time=data['start'],
            end_time=data['end'],
        )
        return _schedule_response(schedule, code=status.HTTP_201_CREATED)


class MarketScheduleListView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        parameters=[MarketScheduleListQuerySerializer],
        responses={200: MarketScheduleListEnvelopeSerializer},
    )
    def get(self, request):
        query = MarketScheduleListQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        schedules = MarketSchedule.objects.all()
        if not request.user.is_staff:
            schedules = schedules.filter(market__user=request.user)
        if market_id := query.validated_data.get('market'):
            schedules = schedules.filter(market_id=market_id)
        return Response(
            ApiResponse(
                success=True,
                code=status.HTTP_200_OK,
                data=MarketScheduleSerializer(schedules, many=True).data,
            )
        )


class MarketScheduleReplaceView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = MarketScheduleReplaceSerializer

    @transaction.atomic
    def put(self, request):
        serializer = MarketScheduleReplaceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        markets = Market.objects.select_for_update()
        if not request.user.is_staff:
            markets = markets.filter(user=request.user)
        market = get_object_or_404(markets, id=data['market'])
        MarketSchedule.objects.filter(market=market).delete()
        schedules = MarketSchedule.objects.bulk_create([
            MarketSchedule(
                market=market,
                day_of_week=item['day'] - 1,
                start_time=item['start'],
                end_time=item['end'],
            )
            for item in data['schedules']
        ])
        return Response(
            ApiResponse(
                success=True,
                code=status.HTTP_200_OK,
                data=MarketScheduleSerializer(schedules, many=True).data,
            )
        )


class MarketScheduleUpdateView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        request=MarketScheduleUpdateSerializer,
        responses={
            200: MarketScheduleEnvelopeSerializer,
            400: OpenApiResponse(description='Invalid or overlapping interval.'),
            404: OpenApiResponse(description='Owned schedule not found.'),
        },
    )
    @transaction.atomic
    def put(self, request, pk):
        schedule = _lock_owned_schedule(schedule_id=pk, user=request.user)
        serializer = MarketScheduleUpdateSerializer(
            data=request.data,
            context={'schedule': schedule},
        )
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        day_of_week = data.get('day', schedule.day_of_week + 1) - 1
        start_time = data.get('start', schedule.start_time)
        end_time = data.get('end', schedule.end_time)
        if _overlapping_schedules(
            market=schedule.market,
            day_of_week=day_of_week,
            start_time=start_time,
            end_time=end_time,
            exclude=schedule.id,
        ).exists():
            raise serializers.ValidationError(
                {'non_field_errors': ['Schedule overlaps an existing interval.']}
            )
        schedule.day_of_week = day_of_week
        schedule.start_time = start_time
        schedule.end_time = end_time
        schedule.save(update_fields=['day_of_week', 'start_time', 'end_time', 'updated_at'])
        return _schedule_response(schedule)


class MarketScheduleDeleteView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        request=None,
        responses={204: None, 404: OpenApiResponse(description='Owned schedule not found.')},
    )
    @transaction.atomic
    def delete(self, request, pk):
        schedule = _lock_owned_schedule(schedule_id=pk, user=request.user)
        schedule.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class MarketScheduleUserListView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        responses={
            200: MarketScheduleListEnvelopeSerializer,
            404: OpenApiResponse(description='Published Market not found.'),
        }
    )
    def get(self, request, pk):
        market = get_object_or_404(Market, id=pk, status=Market.PUBLISHED)
        schedules = MarketSchedule.objects.filter(market=market)
        return Response(
            ApiResponse(
                success=True,
                code=status.HTTP_200_OK,
                data=MarketScheduleSerializer(schedules, many=True).data,
            )
        )
