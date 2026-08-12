from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import permissions, status, views
from rest_framework.response import Response

from apps.market.models import Market
from apps.reserve.models import Reservation, Service
from apps.reserve.serializers.owner import (
    ServiceCreateSerializer,
    ServiceSerializer,
    ServiceUpdateSerializer,
)
from utils.response import ApiResponse


def _owned_services(user):
    return (
        Service.objects.filter(market__user=user)
        .select_related('market', 'market__sub_category')
        .prefetch_related('market__viewed_by')
    )


class ServiceCreateView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        serializer = ServiceCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        market = get_object_or_404(
            Market.objects.select_for_update(),
            id=serializer.validated_data['market'],
            user=request.user,
        )
        service = Service.objects.create(
            market=market,
            name=serializer.validated_data['name'],
        )
        return Response(
            ApiResponse(
                success=True,
                code=status.HTTP_201_CREATED,
                data=ServiceSerializer(service).data,
            ),
            status=status.HTTP_201_CREATED,
        )


class ServiceDetailView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        service = get_object_or_404(_owned_services(request.user), id=pk)
        return Response(
            ApiResponse(
                success=True,
                code=status.HTTP_200_OK,
                data=ServiceSerializer(service).data,
            )
        )


class ServiceListView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(
            ApiResponse(
                success=True,
                code=status.HTTP_200_OK,
                data=ServiceSerializer(_owned_services(request.user), many=True).data,
            )
        )


class ServiceUpdateView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def put(self, request, pk):
        service = get_object_or_404(
            _owned_services(request.user).select_for_update(),
            id=pk,
        )
        serializer = ServiceUpdateSerializer(service, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            ApiResponse(
                success=True,
                code=status.HTTP_200_OK,
                data=ServiceSerializer(service).data,
            )
        )


class ServiceDeleteView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def delete(self, request, pk):
        service = get_object_or_404(
            _owned_services(request.user).select_for_update(),
            id=pk,
        )
        if Reservation.objects.filter(reserve__service=service).exists():
            return Response(
                ApiResponse(
                    success=False,
                    code=status.HTTP_409_CONFLICT,
                    error='Service has reservation history and cannot be deleted.',
                ),
                status=status.HTTP_409_CONFLICT,
            )
        service.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
