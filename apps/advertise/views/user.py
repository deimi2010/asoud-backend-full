from django.db import transaction
from rest_framework import permissions

from apps.advertise.core import public_advertisements
from apps.advertise.models import Advertisement
from apps.advertise.serializers import (
    AdvertiseCreateSerializer,
    AdvertiseListSerializer,
    AdvertiseSerializer,
)
from apps.core.base_views import (
    BaseCreateView,
    BaseDeleteView,
    BaseDetailView,
    BaseListView,
    BaseUpdateView,
)


class AdvertiseCreateView(BaseCreateView):
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        return AdvertiseCreateSerializer

    def post(self, request):
        return self.error_response(
            'Advertisement purchase is unavailable until pricing is configured.',
            503,
        )


class AdvertiseListView(BaseListView):
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        advertisements = (
            public_advertisements()
            .select_related('category')
            .prefetch_related('images')
        )
        if query := self.request.GET.get('q'):
            advertisements = advertisements.filter(name__icontains=query)
        if advert_type := self.request.GET.get('type'):
            advertisements = advertisements.filter(type=advert_type)
        if province := self.request.GET.get('state'):
            advertisements = advertisements.filter(province_id=province)
        if price_gt := self.request.GET.get('price_gt'):
            advertisements = advertisements.filter(price__gte=price_gt)
        if price_lt := self.request.GET.get('price_lt'):
            advertisements = advertisements.filter(price__lte=price_lt)
        return advertisements

    def get_serializer_class(self):
        return AdvertiseListSerializer


class AdvertiseDetailView(BaseDetailView):
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        return (
            public_advertisements()
            .select_related('user', 'category', 'province', 'city', 'product')
            .prefetch_related('images', 'keywords')
        )

    def get_serializer_class(self):
        return AdvertiseSerializer


class AdvertiseOwnListView(BaseListView):
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return (
            Advertisement.objects.filter(user=self.request.user)
            .select_related('category')
            .prefetch_related('images')
        )

    def get_serializer_class(self):
        return AdvertiseListSerializer


class AdvertiseUpdateView(BaseUpdateView):
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Advertisement.objects.filter(user=self.request.user)

    def get_serializer_class(self):
        return AdvertiseCreateSerializer

    @transaction.atomic
    def put(self, request, pk):
        try:
            advertisement = Advertisement.objects.select_for_update().get(
                id=pk,
                user=request.user,
            )
        except Advertisement.DoesNotExist:
            return self.error_response('Advertisement Not Found', 404)
        if advertisement.product_id:
            return self.error_response(
                'Product advertisements are managed by the source product.',
                409,
            )
        serializer = AdvertiseCreateSerializer(
            advertisement,
            data=request.data,
            partial=True,
            context={'request': request, 'owner': request.user},
        )
        serializer.is_valid(raise_exception=True)
        advertisement = serializer.save()
        return self.success_response(data=AdvertiseSerializer(advertisement).data)


class AdvertiseDeleteView(BaseDeleteView):
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Advertisement.objects.filter(user=self.request.user)

    @transaction.atomic
    def delete(self, request, pk):
        try:
            advertisement = Advertisement.objects.select_for_update().get(
                id=pk,
                user=request.user,
            )
        except Advertisement.DoesNotExist:
            return self.error_response('Advertisement Not Found', 404)
        if advertisement.product_id:
            return self.error_response(
                'Product advertisements are managed by the source product.',
                409,
            )
        advertisement.delete()
        return self.success_response(message='Advertisement deleted successfully')


class AdvertisePaymentView(BaseDetailView):
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Advertisement.objects.none()

    def get_serializer_class(self):
        return AdvertiseSerializer

    def get(self, request):
        return self.error_response(
            'Advertisement payment is unavailable until authoritative pricing is configured.',
            503,
        )
