from django.shortcuts import get_object_or_404
from rest_framework import permissions, status, views
from rest_framework.response import Response

from apps.reserve.models import Reservation
from apps.reserve.serializers.owner import ReservationSerializer
from utils.response import ApiResponse


def _owned_reservations(user):
    return (
        Reservation.objects.filter(reserve__service__market__user=user)
        .select_related(
            'user',
            'reserve',
            'reserve__service',
            'reserve__service__market',
            'reserve__service__market__sub_category',
            'specialist',
        )
        .prefetch_related('reserve__service__market__viewed_by')
    )


class ReservationDetailView(views.APIView):
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
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(
            ApiResponse(
                success=True,
                code=status.HTTP_200_OK,
                data=ReservationSerializer(
                    _owned_reservations(request.user),
                    many=True,
                ).data,
            )
        )
