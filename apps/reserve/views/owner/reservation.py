from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import permissions, serializers, status, views
from rest_framework.response import Response

from apps.reserve.models import Reservation
from apps.reserve.lifecycle import notify_after_commit, refund_paid_reservation
from apps.market.access import market_access_filter
from apps.reserve.serializers.owner import ReservationSerializer, ReservationStatusSerializer
from apps.reserve.services import expire_stale_holds
from utils.response import ApiResponse


def _owned_reservations(user):
    modern_access = market_access_filter('service__market__', user)
    legacy_access = market_access_filter('reserve__service__market__', user)
    return (
        Reservation.objects.filter(modern_access | legacy_access).distinct()
        .select_related(
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
        )
        .prefetch_related('reserve__service__market__viewed_by')
        .order_by('-scheduled_start', '-created_at')
    )


class ReservationListQuerySerializer(serializers.Serializer):
    market = serializers.UUIDField(required=False)


class ReservationDetailView(views.APIView):
    serializer_class = ReservationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        reservation = get_object_or_404(_owned_reservations(request.user), id=pk)
        return Response(
            ApiResponse(
                success=True,
                code=status.HTTP_200_OK,
                data=ReservationSerializer(reservation).data,
            )
        )


class ReservationListView(views.APIView):
    serializer_class = ReservationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        expire_stale_holds()
        query = ReservationListQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        reservations = _owned_reservations(request.user)
        if market_id := query.validated_data.get('market'):
            reservations = reservations.filter(
                Q(service__market_id=market_id)
                | Q(reserve__service__market_id=market_id)
            )
        return Response(
            ApiResponse(
                success=True,
                code=status.HTTP_200_OK,
                data=ReservationSerializer(
                    reservations,
                    many=True,
                ).data,
            )
        )


class ReservationStatusView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ReservationStatusSerializer

    @transaction.atomic
    def put(self, request, pk):
        serializer = ReservationStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        authorized_id = get_object_or_404(
            _owned_reservations(request.user).values_list('id', flat=True),
            id=pk,
        )
        reservation = get_object_or_404(
            Reservation.objects.select_for_update(),
            id=authorized_id,
        )
        target = serializer.validated_data['status']
        allowed = {
            Reservation.PENDING_CONFIRMATION: {Reservation.CONFIRMED, Reservation.CANCELLED},
            Reservation.CONFIRMED: {
                Reservation.COMPLETED, Reservation.CANCELLED, Reservation.NO_SHOW,
            },
        }
        if target not in allowed.get(reservation.status, set()):
            return Response(status=status.HTTP_409_CONFLICT)
        reservation.status = target
        fields = ['status', 'updated_at']
        if target == Reservation.CONFIRMED:
            reservation.confirmed_at = timezone.now()
            fields.append('confirmed_at')
        if target == Reservation.CANCELLED:
            reservation.cancelled_at = timezone.now()
            reservation.cancellation_reason = serializer.validated_data.get('reason', '')
            fields.extend(('cancelled_at', 'cancellation_reason'))
        reservation.save(update_fields=fields)
        if target == Reservation.CANCELLED:
            refund_paid_reservation(
                reservation,
                reservation.cancellation_reason or 'لغو نوبت توسط فروشگاه',
            )
            notify_after_commit(reservation, 'cancelled')
        elif target == Reservation.CONFIRMED:
            notify_after_commit(reservation, 'confirmed')
        return Response(ApiResponse(
            success=True, code=200, data=ReservationSerializer(reservation).data,
        ))
