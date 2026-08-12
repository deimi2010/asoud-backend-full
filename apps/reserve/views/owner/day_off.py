from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import permissions, serializers, status, views
from rest_framework.response import Response

from apps.market.models import Market
from apps.reserve.models import DayOff
from apps.reserve.serializers.owner import DayOffCreateSerializer, DayOffSerializer
from utils.response import ApiResponse


class DayOffListQuerySerializer(serializers.Serializer):
    market = serializers.UUIDField(required=False)


class DayOffCreateView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        serializer = DayOffCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        market = get_object_or_404(
            Market.objects.select_for_update(),
            id=data['market'],
            user=request.user,
        )
        day_off, created = DayOff.objects.get_or_create(market=market, date=data['date'])
        response_status = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        return Response(
            ApiResponse(
                success=True,
                code=response_status,
                data=DayOffSerializer(day_off).data,
            ),
            status=response_status,
        )


class DayOffListView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        query = DayOffListQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        days_off = (
            DayOff.objects.filter(market__user=request.user)
            .select_related('market', 'market__sub_category')
            .prefetch_related('market__viewed_by')
        )
        if market_id := query.validated_data.get('market'):
            days_off = days_off.filter(market_id=market_id)
        return Response(
            ApiResponse(
                success=True,
                code=status.HTTP_200_OK,
                data=DayOffSerializer(days_off, many=True).data,
            )
        )


class DayOffDeleteView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def delete(self, request, pk):
        day_off = get_object_or_404(
            DayOff.objects.select_for_update(),
            id=pk,
            market__user=request.user,
        )
        day_off.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
