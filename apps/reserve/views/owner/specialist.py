from django.db import transaction
from django.db.models import Count, F, Q
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
        specialist = Specialist.objects.create(
            user=data['user'],
            field=data.get('field'),
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
            historical_service_ids = set(
                Reservation.objects.filter(specialist=specialist).values_list(
                    'reserve__service_id',
                    flat=True,
                )
            )
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
        if 'user' in data:
            specialist.user = data['user']
        if 'field' in data:
            specialist.field = data['field']
        specialist.save(update_fields=['user', 'field', 'updated_at'])
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
