from django.shortcuts import get_object_or_404
from rest_framework import permissions, serializers, status, views
from rest_framework.response import Response

from apps.market.models import Market
from apps.reserve.models import DayOff, ReserveTime, Service, Specialist
from apps.reserve.serializers.user import (
    DayoffListSerializer,
    ReserveTimeListSerializer,
    ServiceListSerializer,
    SpecialistListSerializer,
)
from utils.response import ApiResponse


class MarketQuerySerializer(serializers.Serializer):
    market = serializers.UUIDField()


class ServiceQuerySerializer(serializers.Serializer):
    service = serializers.UUIDField()


class ServiceListView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        query = MarketQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        market = get_object_or_404(
            Market,
            id=query.validated_data['market'],
            status=Market.PUBLISHED,
        )
        services = (
            Service.objects.filter(market=market)
            .select_related('market', 'market__sub_category')
            .prefetch_related('market__viewed_by')
        )
        if name := request.query_params.get('name'):
            services = services.filter(name=name)
        return Response(
            ApiResponse(
                success=True,
                code=status.HTTP_200_OK,
                data=ServiceListSerializer(services, many=True).data,
            )
        )


class SpecialistListView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        query = ServiceQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        service = get_object_or_404(
            Service.objects.select_related('market'),
            id=query.validated_data['service'],
            market__status=Market.PUBLISHED,
        )
        specialists = Specialist.objects.filter(services=service).distinct()
        return Response(
            ApiResponse(
                success=True,
                code=status.HTTP_200_OK,
                data=SpecialistListSerializer(specialists, many=True).data,
            )
        )


class ReserveTimeListView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        query = ServiceQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        service = get_object_or_404(
            Service.objects.select_related('market'),
            id=query.validated_data['service'],
            market__status=Market.PUBLISHED,
        )
        reserve_times = (
            ReserveTime.objects.filter(service=service)
            .select_related(
                'service',
                'service__market',
                'service__market__sub_category',
            )
            .prefetch_related('service__market__viewed_by')
        )
        return Response(
            ApiResponse(
                success=True,
                code=status.HTTP_200_OK,
                data=ReserveTimeListSerializer(reserve_times, many=True).data,
            )
        )


class DayOffListView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        query = MarketQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        market = get_object_or_404(
            Market,
            id=query.validated_data['market'],
            status=Market.PUBLISHED,
        )
        days_off = (
            DayOff.objects.filter(market=market)
            .select_related('market', 'market__sub_category')
            .prefetch_related('market__viewed_by')
        )
        return Response(
            ApiResponse(
                success=True,
                code=status.HTTP_200_OK,
                data=DayoffListSerializer(days_off, many=True).data,
            )
        )
