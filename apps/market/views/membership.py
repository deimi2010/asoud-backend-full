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
from apps.users.models import UserDocument, UserProfile
from django.utils import timezone


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
                'permissions': serializer.validated_data.get('permissions', []),
                'status': MarketMembership.PROFILE_INCOMPLETE,
                'is_active': False,
                'invited_by': request.user,
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
        if 'permissions' in serializer.validated_data:
            membership.permissions = serializer.validated_data['permissions']
        enable = serializer.validated_data.get('is_active')
        if enable is False:
            membership.is_active = False
            membership.status = MarketMembership.OWNER_DISABLED
        elif enable is True:
            profile_approved = UserProfile.objects.filter(
                user=membership.user, status=UserProfile.APPROVED,
                phone_ownership_status=UserProfile.PHONE_OWNER_MATCHED,
            ).exists()
            required = len(UserDocument.DOCUMENT_TYPE_CHOICES)
            documents_approved = UserDocument.objects.filter(
                user=membership.user, status=UserDocument.APPROVED,
            ).values('document_type').distinct().count() == required
            if not (profile_approved and documents_approved):
                membership.status = MarketMembership.PROFILE_INCOMPLETE
                membership.is_active = False
            else:
                membership.status = MarketMembership.ADMIN_REVIEW
                membership.owner_approved_at = timezone.now()
                membership.is_active = False
        membership.save(update_fields=(
            'role', 'permissions', 'status', 'is_active', 'owner_approved_at', 'updated_at',
        ))
        return Response(MarketMembershipSerializer(membership).data)

    @extend_schema(request=None, responses={204: None}, tags=['Store membership'])
    @transaction.atomic
    def delete(self, request, pk):
        membership = get_object_or_404(
            _administered_memberships(request.user).select_for_update(),
            id=pk,
        )
        membership.is_active = False
        membership.status = MarketMembership.OWNER_DISABLED
        membership.save(update_fields=('is_active', 'status', 'updated_at'))
        return Response(status=status.HTTP_204_NO_CONTENT)
