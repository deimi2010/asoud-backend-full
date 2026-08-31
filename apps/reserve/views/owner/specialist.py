from django.db import transaction
from django.db.models import Q
from django.db.models import Count, F
from django.shortcuts import get_object_or_404
from rest_framework import permissions, serializers, status, views
from rest_framework.response import Response

from apps.reserve.models import Reservation, Service, Specialist
from apps.market.access import market_access_filter
from apps.reserve.serializers.owner import (
    SpecialistCreateSerializer,
    SpecialistSerializer,
    SpecialistUpdateSerializer,
)
from utils.response import ApiResponse


def _fully_owned_specialists(user):
    access = market_access_filter('services__market__', user, write=True)
    return (
        Specialist.objects.annotate(
            service_count=Count('services', distinct=True),
            owned_service_count=Count(
                'services',
                filter=access,
                distinct=True,
            ),
        )
        .filter(service_count__gt=0, service_count=F('owned_service_count'))
        .prefetch_related(
            'services__market__sub_category',
            'services__market__viewed_by',
        )
    )


def _owned_services(service_ids, user):
    services = list(
        Service.objects.filter(
            market_access_filter('market__', user, write=True),
            id__in=service_ids,
        ).distinct().select_related('market')
    )
    if len(services) != len(service_ids):
        raise serializers.ValidationError(
            {'services': 'Every service must exist and belong to you.'}
        )
    return services


def _lock_fully_owned_specialist(specialist_id, user):
    candidate = get_object_or_404(_fully_owned_specialists(user), id=specialist_id)
    return get_object_or_404(
        Specialist.objects.select_for_update(),
        id=candidate.id,
    )


class SpecialistCreateView(views.APIView):
    serializer_class = SpecialistCreateSerializer
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        serializer = SpecialistCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        services = _owned_services(data['services'], request.user)
        market_ids = {service.market_id for service in services}
        if len(market_ids) != 1:
            raise serializers.ValidationError(
                {'services': 'All specialist services must belong to one store.'}
            )
        market_id = market_ids.pop()
        requested_market = data.get('market')
        if requested_market is not None and requested_market.id != market_id:
            raise serializers.ValidationError({'market': 'Store does not match the services.'})
        specialist = Specialist.objects.create(
            market_id=market_id,
            account=data.get('account'),
            user=data['user'],
            field=data.get('field'),
            is_active=data.get('is_active', True),
        )
        specialist.services.set(services)
        specialist = _fully_owned_specialists(request.user).get(id=specialist.id)
        return Response(
            ApiResponse(
                success=True,
                code=status.HTTP_201_CREATED,
                data=SpecialistSerializer(specialist).data,
            ),
            status=status.HTTP_201_CREATED,
        )


class SpecialistDetailView(views.APIView):
    serializer_class = SpecialistSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        specialist = get_object_or_404(_fully_owned_specialists(request.user), id=pk)
        return Response(
            ApiResponse(
                success=True,
                code=status.HTTP_200_OK,
                data=SpecialistSerializer(specialist).data,
            )
        )


class SpecialistListView(views.APIView):
    serializer_class = SpecialistSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(
            ApiResponse(
                success=True,
                code=status.HTTP_200_OK,
                data=SpecialistSerializer(
                    _fully_owned_specialists(request.user),
                    many=True,
                ).data,
            )
        )


class SpecialistUpdateView(views.APIView):
    serializer_class = SpecialistUpdateSerializer
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def put(self, request, pk):
        specialist = _lock_fully_owned_specialist(pk, request.user)
        serializer = SpecialistUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        if 'services' in data:
            services = _owned_services(data['services'], request.user)
            if len({service.market_id for service in services}) != 1:
                raise serializers.ValidationError(
                    {'services': 'All specialist services must belong to one store.'}
                )
            historical_service_ids = set(
                Reservation.objects.filter(specialist=specialist)
                .filter(Q(service__isnull=False) | Q(reserve__service__isnull=False))
                .values_list('service_id', 'reserve__service_id')
            )
            historical_service_ids = {
                direct_id or legacy_id
                for direct_id, legacy_id in historical_service_ids
                if direct_id or legacy_id
            }
            if not historical_service_ids.issubset({service.id for service in services}):
                return Response(
                    ApiResponse(
                        success=False,
                        code=status.HTTP_409_CONFLICT,
                        error='Historically booked services cannot be removed.',
                    ),
                    status=status.HTTP_409_CONFLICT,
                )
            specialist.services.set(services)
            specialist.market_id = services[0].market_id
        if 'account' in data:
            specialist.account = data['account']
        if 'user' in data:
            specialist.user = data['user']
        if 'field' in data:
            specialist.field = data['field']
        if 'is_active' in data:
            specialist.is_active = data['is_active']
        specialist.save(update_fields=[
            'market', 'account', 'user', 'field', 'is_active', 'updated_at',
        ])
        specialist = _fully_owned_specialists(request.user).get(id=specialist.id)
        return Response(
            ApiResponse(
                success=True,
                code=status.HTTP_200_OK,
                data=SpecialistSerializer(specialist).data,
            )
        )


class SpecialistDeleteView(views.APIView):
    serializer_class = SpecialistSerializer
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def delete(self, request, pk):
        specialist = _lock_fully_owned_specialist(pk, request.user)
        if Reservation.objects.filter(specialist=specialist).exists():
            return Response(
                ApiResponse(
                    success=False,
                    code=status.HTTP_409_CONFLICT,
                    error='Specialist has reservation history and cannot be deleted.',
                ),
                status=status.HTTP_409_CONFLICT,
            )
        specialist.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
