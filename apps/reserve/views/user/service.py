from django.shortcuts import get_object_or_404
from django.db.models import Q
from rest_framework import permissions, serializers, status, views
from rest_framework.response import Response

from apps.market.models import Market
from apps.product.models import Product
from apps.reserve.models import DayOff, ReserveTime, Service, Specialist
from apps.reserve.serializers.user import (
    AvailabilityQuerySerializer,
    DayoffListSerializer,
    ReserveTimeListSerializer,
    ServiceListSerializer,
    SpecialistListSerializer,
)
from apps.reserve.services import available_slots
from utils.response import ApiResponse


class MarketQuerySerializer(serializers.Serializer):
    market = serializers.UUIDField()


class ServiceQuerySerializer(serializers.Serializer):
    service = serializers.UUIDField()


class ServiceListView(views.APIView):
    serializer_class = ServiceListSerializer
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
            Service.objects.filter(market=market, is_active=True)
            .filter(
                Q(product__isnull=True)
                | Q(product__type=Product.SERVICE, product__status=Product.PUBLISHED)
            )
            .distinct()
            .select_related('market', 'market__sub_category', 'product')
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
    serializer_class = SpecialistListSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        query = ServiceQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        service = get_object_or_404(
            Service.objects.select_related('market'),
            id=query.validated_data['service'],
            market__status=Market.PUBLISHED,
        )
        specialists = Specialist.objects.filter(
            services=service, is_active=True,
        ).distinct()
        return Response(
            ApiResponse(
                success=True,
                code=status.HTTP_200_OK,
                data=SpecialistListSerializer(specialists, many=True).data,
            )
        )


class ReserveTimeListView(views.APIView):
    serializer_class = ReserveTimeListSerializer
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
    serializer_class = DayoffListSerializer
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


class AvailabilityView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = AvailabilityQuerySerializer

    def get(self, request):
        query = AvailabilityQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        data = query.validated_data
        service = get_object_or_404(
            Service.objects.select_related('market', 'product'),
            id=data['service'],
            is_active=True,
            market__status=Market.PUBLISHED,
        )
        specialist = get_object_or_404(
            Specialist.objects.filter(services=service),
            id=data['specialist'],
            is_active=True,
        )
        slots = available_slots(
            service=service,
            specialist=specialist,
            day=data['date'],
        )
        return Response(ApiResponse(success=True, code=200, data={
            'date': data['date'].isoformat(),
            'is_day_off': DayOff.objects.filter(
                market=service.market, date=data['date'],
            ).exists(),
            'slots': [
                {
                    'start': item['start'].isoformat(),
                    'end': item['end'].isoformat(),
                    'capacity': item['capacity'],
                    'remaining': item['remaining'],
                    'available': item['available'],
                }
                for item in slots
            ],
        }))
