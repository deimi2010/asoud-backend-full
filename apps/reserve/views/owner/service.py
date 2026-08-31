from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import permissions, status, views
from rest_framework.response import Response

from apps.market.access import accessible_markets, lock_accessible_market, market_access_filter
from apps.product.models import Product
from apps.reserve.models import Reservation, Service
from apps.reserve.serializers.owner import (
    AppointmentProductSerializer,
    ServiceCreateSerializer,
    ServiceSerializer,
    ServiceUpdateSerializer,
)
from utils.response import ApiResponse


def _accessible_services(user, *, write=False):
    return (
        Service.objects.filter(market_access_filter('market__', user, write=write))
        .distinct()
        .select_related('market', 'market__sub_category')
        .prefetch_related('market__viewed_by')
    )


class AppointmentProductListView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = AppointmentProductSerializer

    def get(self, request):
        market = get_object_or_404(
            accessible_markets(request.user),
            id=request.query_params.get('market'),
        )
        products = Product.objects.filter(
            market=market,
            type=Product.SERVICE,
        ).select_related('appointment_service').order_by('name')
        return Response(ApiResponse(
            success=True,
            code=200,
            data=AppointmentProductSerializer(products, many=True).data,
        ))


class ServiceCreateView(views.APIView):
    serializer_class = ServiceCreateSerializer
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        serializer = ServiceCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        market = lock_accessible_market(
            market_id=serializer.validated_data['market'],
            user=request.user,
            write=True,
        )
        product = None
        if product_id := serializer.validated_data.get('product'):
            product = get_object_or_404(
                Product.objects.select_for_update(),
                id=product_id,
                market=market,
                type=Product.SERVICE,
            )
            existing = Service.objects.filter(product=product).first()
            if existing is not None:
                return Response(
                    ApiResponse(
                        success=True,
                        code=status.HTTP_200_OK,
                        data=ServiceSerializer(existing).data,
                    )
                )
        config = {
            key: value
            for key, value in serializer.validated_data.items()
            if key not in ('market', 'product', 'name')
        }
        service = Service.objects.create(
            market=market,
            product=product,
            name=product.name[:32] if product else serializer.validated_data['name'],
            **config,
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
    serializer_class = ServiceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        service = get_object_or_404(_accessible_services(request.user), id=pk)
        return Response(
            ApiResponse(
                success=True,
                code=status.HTTP_200_OK,
                data=ServiceSerializer(service).data,
            )
        )


class ServiceListView(views.APIView):
    serializer_class = ServiceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(
            ApiResponse(
                success=True,
                code=status.HTTP_200_OK,
                data=ServiceSerializer(_accessible_services(request.user), many=True).data,
            )
        )


class ServiceUpdateView(views.APIView):
    serializer_class = ServiceUpdateSerializer
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def put(self, request, pk):
        authorized_id = get_object_or_404(
            _accessible_services(request.user, write=True).values('id'), id=pk,
        )['id']
        service = get_object_or_404(
            Service.objects.select_for_update(), id=authorized_id,
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
    serializer_class = ServiceSerializer
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def delete(self, request, pk):
        authorized_id = get_object_or_404(
            _accessible_services(request.user, write=True).values('id'), id=pk,
        )['id']
        service = get_object_or_404(
            Service.objects.select_for_update(), id=authorized_id,
        )
        if Reservation.objects.filter(
            Q(service=service) | Q(reserve__service=service)
        ).exists():
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
