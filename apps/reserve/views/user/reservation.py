from datetime import timedelta

from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import permissions, status, views
from rest_framework.response import Response

from apps.market.models import Market
from apps.reserve.models import Reservation, ReserveTime, Service, Specialist
from apps.reserve.lifecycle import notify_after_commit, refund_paid_reservation
from apps.reserve.serializers.owner import ReservationSerializer
from apps.reserve.serializers.user import (
    ReservationCancelSerializer,
    ReservationCreateSerializer,
    ReservationListQuerySerializer,
    ReservationRescheduleSerializer,
)
from apps.reserve.services import available_slots, expire_stale_holds, hold_reservation
from utils.response import ApiResponse


def _reservation_queryset():
    return Reservation.objects.select_related(
        'user',
        'reserve',
        'reserve__service',
        'reserve__service__market',
        'reserve__service__market__sub_category',
        'service',
        'service__market',
        'service__market__location',
        'service__market__contact',
        'service__product',
        'specialist',
    ).prefetch_related(
        'reserve__service__market__viewed_by',
    ).order_by('-scheduled_start', '-created_at')


class ReservationListView(views.APIView):
    serializer_class = ReservationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        expire_stale_holds()
        query = ReservationListQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        reservations = _reservation_queryset().filter(user=request.user)
        if market_id := query.validated_data.get('market'):
            reservations = reservations.filter(
                Q(service__market_id=market_id)
                | Q(reserve__service__market_id=market_id)
            )
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
        if serializer.validated_data.get('service'):
            service = get_object_or_404(
                Service.objects.select_related('market', 'product'),
                id=serializer.validated_data['service'],
                is_active=True,
                market__status=Market.PUBLISHED,
            )
            specialist = serializer.validated_data['specialist']
            try:
                reservation = hold_reservation(
                    user=request.user,
                    service=service,
                    specialist=specialist,
                    scheduled_start=serializer.validated_data['scheduled_start'],
                )
            except (Specialist.DoesNotExist, Service.DoesNotExist, ValueError) as exc:
                return Response(
                    ApiResponse(success=False, code=409, error={
                        'code': 'slot_unavailable', 'detail': str(exc),
                    }),
                    status=status.HTTP_409_CONFLICT,
                )
            reservation = _reservation_queryset().get(id=reservation.id)
            if reservation.status == Reservation.PENDING_CONFIRMATION:
                notify_after_commit(reservation, 'requested')
            elif reservation.status == Reservation.CONFIRMED:
                notify_after_commit(reservation, 'confirmed')
            return Response(
                ApiResponse(
                    success=True,
                    code=status.HTTP_201_CREATED,
                    data=ReservationSerializer(reservation).data,
                ),
                status=status.HTTP_201_CREATED,
            )
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


class ReservationTrackingDetailView(views.APIView):
    serializer_class = ReservationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, tracking_code):
        reservation = get_object_or_404(
            _reservation_queryset(),
            tracking_code=tracking_code,
            user=request.user,
        )
        return Response(ApiResponse(
            success=True,
            code=status.HTTP_200_OK,
            data=ReservationSerializer(reservation).data,
        ))


class ReservationCancelView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ReservationCancelSerializer

    @transaction.atomic
    def post(self, request, pk):
        serializer = ReservationCancelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reservation = get_object_or_404(
            Reservation.objects.select_for_update(),
            id=pk,
            user=request.user,
            status__in=(
                Reservation.HELD,
                Reservation.PENDING_CONFIRMATION,
                Reservation.CONFIRMED,
            ),
        )
        if (
            reservation.scheduled_start
            and reservation.service_id
            and reservation.status != Reservation.HELD
            and reservation.scheduled_start
            <= timezone.now() + timedelta(hours=reservation.service.cancellation_hours)
        ):
            return Response(
                ApiResponse(success=False, code=409, error={
                    'code': 'cancellation_window_closed',
                    'detail': 'The cancellation window has closed.',
                }),
                status=status.HTTP_409_CONFLICT,
            )
        reservation.status = Reservation.CANCELLED
        reservation.cancelled_at = timezone.now()
        reservation.cancellation_reason = serializer.validated_data.get('reason', '')
        reservation.save(update_fields=(
            'status', 'cancelled_at', 'cancellation_reason', 'updated_at',
        ))
        refund_paid_reservation(
            reservation,
            reservation.cancellation_reason or 'لغو نوبت توسط مشتری',
        )
        notify_after_commit(reservation, 'cancelled')
        return Response(ApiResponse(
            success=True, code=200, data=ReservationSerializer(reservation).data,
        ))


class ReservationRescheduleView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ReservationRescheduleSerializer

    @transaction.atomic
    def put(self, request, pk):
        serializer = ReservationRescheduleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reservation = get_object_or_404(
            Reservation.objects.select_for_update(),
            id=pk,
            user=request.user,
            service__isnull=False,
            status__in=(Reservation.PENDING_CONFIRMATION, Reservation.CONFIRMED),
        )
        if reservation.scheduled_start <= timezone.now() + timedelta(
            hours=reservation.service.cancellation_hours,
        ):
            return Response(status=status.HTTP_409_CONFLICT)
        specialist = Specialist.objects.select_for_update().get(
            id=reservation.specialist_id,
            is_active=True,
        )
        new_start = serializer.validated_data['scheduled_start']
        slot = next((item for item in available_slots(
            service=reservation.service,
            specialist=specialist,
            day=timezone.localtime(new_start).date(),
            exclude_reservation_id=reservation.id,
        ) if item['start'] == new_start and item['available']), None)
        if slot is None:
            return Response(status=status.HTTP_409_CONFLICT)
        reservation.scheduled_start = slot['start']
        reservation.scheduled_end = slot['end']
        reservation.status = (
            Reservation.PENDING_CONFIRMATION
            if reservation.service.requires_owner_confirmation
            else Reservation.CONFIRMED
        )
        reservation.reminder_24h_sent_at = None
        reservation.reminder_2h_sent_at = None
        reservation.save(update_fields=(
            'scheduled_start', 'scheduled_end', 'status',
            'reminder_24h_sent_at', 'reminder_2h_sent_at', 'updated_at',
        ))
        notify_after_commit(reservation, 'rescheduled')
        return Response(ApiResponse(
            success=True, code=200, data=ReservationSerializer(reservation).data,
        ))
