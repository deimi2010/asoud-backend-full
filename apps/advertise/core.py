from django.db import transaction
from django.db.models import Q

from apps.advertise.models import Advertisement
from apps.advertise.serializers import AdvertiseCreateSerializer, AdvertiseSerializer


def public_advertisements():
    return Advertisement.objects.filter(is_paid=True).filter(
        Q(product__isnull=True)
        | Q(product__status='published', product__market__status='published')
    )


class AdvertisementCore:
    @staticmethod
    def create_advertisement(request):
        serializer = AdvertiseCreateSerializer(
            data=request.data,
            context={'request': request, 'owner': request.user},
        )
        serializer.is_valid(raise_exception=True)
        advertisement = serializer.save(user=request.user)
        return AdvertiseSerializer(advertisement).data

    @staticmethod
    @transaction.atomic
    def create_advertisement_for_product(product):
        advertisement, _ = Advertisement.objects.update_or_create(
            product=product,
            defaults={
                'user': product.market.user,
                'type': product.type,
                'name': product.name,
                'description': product.description or '',
                'price': product.main_price,
                'category': product.sub_category.category,
                # Product.is_requirement is client-controlled. It may create a
                # draft projection, but cannot bypass the missing paid-ad flow.
                'is_paid': False,
            },
        )
        return AdvertiseSerializer(advertisement).data
