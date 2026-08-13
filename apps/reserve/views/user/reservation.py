from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import permissions, status, views
from rest_framework.response import Response

from apps.market.models import Market
from apps.reserve.models import Reservation, ReserveTime, Service, Specialist
from apps.reserve.serializers.owner import ReservationSerializer
from apps.reserve.serializers.user import ReservationCreateSerializer
from utils.response import ApiResponse


def _reservation_queryset():
    return Reservation.objects.select_related(
        'user',
        'reserve',
        'reserve__service',
        'reserve__service__market',
        'reserve__service__market__sub_category',
        'specialist',
    ).prefetch_related(
        'reserve__service__market__viewed_by',
    )


class ReservationListView(views.APIView):
    serializer_class = ReservationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        reservations = _reservation_queryset().filter(user=request.user)
        return Response(
            ApiResponse(
                success=True,
                code=status.HTTP_200_OK,
                data=ReservationSerializer(reservations, many=True).data,
            )
        )


class ReservationDetailView(views.APIView):
    serializer_class = ReservationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        reservation = get_object_or_404(
            _reservation_queryset(),
            id=pk,
            user=request.user,
        )
        return Response(
            ApiResponse(
                success=True,
                code=status.HTTP_200_OK,
                data=ReservationSerializer(reservation).data,
            )
        )


class ReservationCreateView(views.APIView):
    serializer_class = ReservationCreateSerializer
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        serializer = ReservationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        specialist = get_object_or_404(
            Specialist.objects.select_for_update(),
            id=serializer.validated_data['specialist'].id,
        )
        reserve_candidate = get_object_or_404(
            ReserveTime.objects.only('service_id'),
            id=serializer.validated_data['reserve'],
            service__market__status=Market.PUBLISHED,
        )
        service = get_object_or_404(
            Service.objects.select_for_update(),
            id=reserve_candidate.service_id,
            market__status=Market.PUBLISHED,
        )
        reserve = get_object_or_404(
            ReserveTime.objects.select_for_update(),
            id=serializer.validated_data['reserve'],
            service=service,
        )
        if not specialist.services.filter(
            id=reserve.service_id,
            market__status=Market.PUBLISHED,
        ).exists():
            return Response(
                ApiResponse(
                    success=False,
                    code=status.HTTP_400_BAD_REQUEST,
                    error='Specialist Does Not Provide This Service',
                ),
                status=status.HTTP_400_BAD_REQUEST,
            )
        reservation = Reservation.objects.create(
            user=request.user,
            reserve=reserve,
            specialist=specialist,
            is_paid=False,
        )
        reservation = _reservation_queryset().get(id=reservation.id)
        return Response(
            ApiResponse(
                success=True,
                code=status.HTTP_201_CREATED,
                data=ReservationSerializer(reservation).data,
            ),
            status=status.HTTP_201_CREATED,
        )
