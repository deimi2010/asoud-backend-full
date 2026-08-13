from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import permissions, status, views
from rest_framework.response import Response

from apps.reserve.models import Reservation, ReserveTime, Service
from apps.market.access import market_access_filter
from apps.reserve.serializers.owner import (
    ReserveTimeCreateSerializer,
    ReserveTimeSerializer,
    ReserveTimeUpdateSerializer,
)
from utils.response import ApiResponse


def _owned_reserve_times(user):
    return (
        ReserveTime.objects.filter(
            market_access_filter('service__market__', user)
        ).distinct()
        .select_related(
            'service',
            'service__market',
            'service__market__sub_category',
        )
        .prefetch_related('service__market__viewed_by')
    )


def _lock_owned_reserve_time(reserve_id, user):
    access = market_access_filter('service__market__', user, write=True)
    candidate = get_object_or_404(
        ReserveTime.objects.only('service_id').filter(access),
        id=reserve_id,
    )
    authorized_service_id = get_object_or_404(
        Service.objects.filter(market_access_filter('market__', user, write=True))
        .values('id'),
        id=candidate.service_id,
    )['id']
    service = get_object_or_404(
        Service.objects.select_for_update(), id=authorized_service_id,
    )
    return get_object_or_404(
        ReserveTime.objects.select_for_update(),
        id=reserve_id,
        service=service,
    )


class ReserveTimeCreateView(views.APIView):
    serializer_class = ReserveTimeCreateSerializer
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        serializer = ReserveTimeCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        authorized_service_id = get_object_or_404(
            Service.objects.filter(
                market_access_filter('market__', request.user, write=True)
            ).values('id'),
            id=data['service'],
        )['id']
        service = get_object_or_404(
            Service.objects.select_for_update(), id=authorized_service_id,
        )
        reserve = ReserveTime.objects.filter(service=service, day=data['day']).first()
        response_status = status.HTTP_200_OK
        if reserve is None:
            reserve = ReserveTime(service=service)
            response_status = status.HTTP_201_CREATED
        elif Reservation.objects.filter(reserve=reserve).exists() and (
            reserve.start != data['start'] or reserve.end != data.get('end')
        ):
            return Response(
                ApiResponse(
                    success=False,
                    code=status.HTTP_409_CONFLICT,
                    error='Booked reserve time cannot be changed.',
                ),
                status=status.HTTP_409_CONFLICT,
            )
        reserve.day = data['day']
        reserve.start = data['start']
        reserve.end = data.get('end')
        reserve.save()
        return Response(
            ApiResponse(
                success=True,
                code=response_status,
                data=ReserveTimeSerializer(reserve).data,
            ),
            status=response_status,
        )


class ReserveTimeDetailView(views.APIView):
    serializer_class = ReserveTimeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        reserve = get_object_or_404(_owned_reserve_times(request.user), id=pk)
        return Response(
            ApiResponse(
                success=True,
                code=status.HTTP_200_OK,
                data=ReserveTimeSerializer(reserve).data,
            )
        )


class ReserveTimeListView(views.APIView):
    serializer_class = ReserveTimeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(
            ApiResponse(
                success=True,
                code=status.HTTP_200_OK,
                data=ReserveTimeSerializer(
                    _owned_reserve_times(request.user),
                    many=True,
                ).data,
            )
        )


class ReserveTimeUpdateView(views.APIView):
    serializer_class = ReserveTimeUpdateSerializer
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def put(self, request, pk):
        reserve = _lock_owned_reserve_time(pk, request.user)
        serializer = ReserveTimeUpdateSerializer(reserve, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        changes_history = any(
            getattr(reserve, field) != value
            for field, value in serializer.validated_data.items()
        )
        if Reservation.objects.filter(reserve=reserve).exists() and changes_history:
            return Response(
                ApiResponse(
                    success=False,
                    code=status.HTTP_409_CONFLICT,
                    error='Booked reserve time cannot be changed.',
                ),
                status=status.HTTP_409_CONFLICT,
            )
        serializer.save()
        return Response(
            ApiResponse(
                success=True,
                code=status.HTTP_200_OK,
                data=ReserveTimeSerializer(reserve).data,
            )
        )


class ReserveTimeDeleteView(views.APIView):
    serializer_class = ReserveTimeSerializer
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def delete(self, request, pk):
        reserve = _lock_owned_reserve_time(pk, request.user)
        if Reservation.objects.filter(reserve=reserve).exists():
            return Response(
                ApiResponse(
                    success=False,
                    code=status.HTTP_409_CONFLICT,
                    error='Reserve time has reservation history and cannot be deleted.',
                ),
                status=status.HTTP_409_CONFLICT,
            )
        reserve.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
