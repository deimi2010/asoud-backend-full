from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status, views
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema

from apps.core.permissions import IsStoreOwner
from apps.market.models import Market, MarketMembership
from apps.market.serializers.membership import (
    MarketMembershipInputSerializer,
    MarketMembershipSerializer,
    MarketMembershipUpdateSerializer,
)
from apps.users.models import User


def _administered_markets(user):
    markets = Market.objects.all()
    return markets if user.is_staff else markets.filter(user=user)


def _administered_memberships(user):
    memberships = MarketMembership.objects.select_related('market', 'user')
    return memberships if user.is_staff else memberships.filter(market__user=user)


class MarketMembershipListCreateView(views.APIView):
    permission_classes = [IsStoreOwner]

    @extend_schema(responses={200: MarketMembershipSerializer(many=True)}, tags=['Store membership'])
    def get(self, request, market_id):
        market = get_object_or_404(_administered_markets(request.user), id=market_id)
        memberships = market.memberships.select_related('user').order_by('created_at')
        return Response(MarketMembershipSerializer(memberships, many=True).data)

    @extend_schema(
        request=MarketMembershipInputSerializer,
        responses={200: MarketMembershipSerializer, 201: MarketMembershipSerializer},
        tags=['Store membership'],
    )
    @transaction.atomic
    def post(self, request, market_id):
        serializer = MarketMembershipInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        market = get_object_or_404(
            _administered_markets(request.user).select_for_update(),
            id=market_id,
        )
        colleague = get_object_or_404(
            User.objects.filter(is_active=True),
            mobile_number=serializer.validated_data['mobile_number'],
        )
        if colleague.id == market.user_id:
            return Response(
                {'detail': 'The store owner cannot also be a colleague.'},
                status=status.HTTP_409_CONFLICT,
            )
        membership, created = MarketMembership.objects.update_or_create(
            market=market,
            user=colleague,
            defaults={
                'role': serializer.validated_data['role'],
                'is_active': True,
            },
        )
        return Response(
            MarketMembershipSerializer(membership).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class MarketMembershipDetailView(views.APIView):
    permission_classes = [IsStoreOwner]

    @extend_schema(
        request=MarketMembershipUpdateSerializer,
        responses={200: MarketMembershipSerializer},
        tags=['Store membership'],
    )
    @transaction.atomic
    def put(self, request, pk):
        serializer = MarketMembershipUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        membership = get_object_or_404(
            _administered_memberships(request.user).select_for_update(),
            id=pk,
        )
        membership.role = serializer.validated_data['role']
        membership.is_active = True
        membership.save(update_fields=('role', 'is_active', 'updated_at'))
        return Response(MarketMembershipSerializer(membership).data)

    @extend_schema(request=None, responses={204: None}, tags=['Store membership'])
    @transaction.atomic
    def delete(self, request, pk):
        membership = get_object_or_404(
            _administered_memberships(request.user).select_for_update(),
            id=pk,
        )
        membership.is_active = False
        membership.save(update_fields=('is_active', 'updated_at'))
        return Response(status=status.HTTP_204_NO_CONTENT)
