from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import permissions, serializers, status, views
from rest_framework.response import Response

from apps.core.permissions import IsAuthenticatedUser
from apps.market.models import BusinessCardProfile
from apps.market.serializers.business_card import (
    BusinessCardSerializer,
    BusinessCardWriteSerializer,
)
from utils.response import ApiResponse


def _card_queryset():
    return BusinessCardProfile.objects.select_related(
        'market',
        'market__sub_category',
        'market__sub_category__category__group',
        'market__contact',
        'market__location__city__province__country',
    )


class BusinessCardListCreateView(views.APIView):
    permission_classes = [IsAuthenticatedUser]
    serializer_class = BusinessCardSerializer

    @extend_schema(operation_id='owner_business_card_list')
    def get(self, request):
        cards = _card_queryset().filter(market__user=request.user)
        data = BusinessCardSerializer(
            cards, many=True, context={'request': request},
        ).data
        return Response(ApiResponse(success=True, code=200, data=data))

    @extend_schema(
        operation_id='owner_business_card_create',
        request=BusinessCardWriteSerializer,
        responses={201: BusinessCardSerializer},
    )
    def post(self, request):
        serializer = BusinessCardWriteSerializer(
            data=request.data, context={'request': request},
        )
        serializer.is_valid(raise_exception=True)
        card = serializer.save()
        data = BusinessCardSerializer(card, context={'request': request}).data
        return Response(
            ApiResponse(success=True, code=201, data=data),
            status=status.HTTP_201_CREATED,
        )


class BusinessCardDetailView(views.APIView):
    permission_classes = [IsAuthenticatedUser]
    serializer_class = BusinessCardSerializer

    def _get(self, request, pk):
        return _card_queryset().filter(pk=pk, market__user=request.user).first()

    @extend_schema(operation_id='owner_business_card_retrieve')
    def get(self, request, pk):
        card = self._get(request, pk)
        if card is None:
            return Response({'error': 'Business card not found.'}, status=404)
        return Response(ApiResponse(
            success=True,
            code=200,
            data=BusinessCardSerializer(card, context={'request': request}).data,
        ))

    @extend_schema(
        operation_id='owner_business_card_update',
        request=BusinessCardWriteSerializer,
        responses=BusinessCardSerializer,
    )
    def patch(self, request, pk):
        card = self._get(request, pk)
        if card is None:
            return Response({'error': 'Business card not found.'}, status=404)
        serializer = BusinessCardWriteSerializer(
            card,
            data=request.data,
            partial=True,
            context={'request': request},
        )
        serializer.is_valid(raise_exception=True)
        card = serializer.save()
        card = _card_queryset().get(pk=card.pk)
        return Response(ApiResponse(
            success=True,
            code=200,
            data=BusinessCardSerializer(card, context={'request': request}).data,
        ))


class BusinessCardLifecycleView(views.APIView):
    permission_classes = [IsAuthenticatedUser]
    serializer_class = BusinessCardSerializer

    @transaction.atomic
    @extend_schema(
        operation_id='owner_business_card_lifecycle',
        request=None,
        responses=BusinessCardSerializer,
    )
    def post(self, request, pk, action):
        card = BusinessCardProfile.objects.select_for_update().select_related(
            'market',
        ).filter(pk=pk, market__user=request.user).first()
        if card is None:
            return Response({'error': 'Business card not found.'}, status=404)

        if action == 'queue':
            if not card.is_paid or (
                card.subscription_end_date is not None
                and card.subscription_end_date <= timezone.now()
            ):
                raise serializers.ValidationError({
                    'payment': 'Business card subscription payment is required.'
                })
            if not hasattr(card.market, 'contact') or not hasattr(card.market, 'location'):
                raise serializers.ValidationError({
                    'profile': 'Contact and location information must be completed.'
                })
            card.status = BusinessCardProfile.QUEUE
            card.status_reason = ''
        elif action == 'unpublish':
            card.status = BusinessCardProfile.DRAFT
            card.status_reason = ''
        elif action == 'inactive':
            card.status = BusinessCardProfile.INACTIVE
        else:
            return Response({'error': 'Unsupported action.'}, status=400)
        card.save(update_fields=('status', 'status_reason', 'updated_at'))
        card = _card_queryset().get(pk=card.pk)
        return Response(ApiResponse(
            success=True,
            code=200,
            data=BusinessCardSerializer(card, context={'request': request}).data,
        ))


class PublicBusinessCardView(views.APIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = BusinessCardSerializer

    @extend_schema(operation_id='public_business_card_retrieve')
    def get(self, request, business_id):
        now = timezone.now()
        card = _card_queryset().filter(
            market__business_id=business_id,
            status=BusinessCardProfile.PUBLISHED,
            is_paid=True,
        ).filter(
            Q(subscription_end_date__isnull=True) | Q(subscription_end_date__gt=now)
        ).first()
        if card is None:
            return Response({'error': 'Business card not found.'}, status=404)
        data = dict(BusinessCardSerializer(
            card, context={'request': request},
        ).data)
        for private_field in (
            'national_code', 'market_id', 'status_reason', 'is_paid',
            'subscription_start_date', 'subscription_end_date',
            'subscription_fee',
            'subscription_active',
        ):
            data.pop(private_field, None)
        return Response(ApiResponse(success=True, code=200, data=data))
