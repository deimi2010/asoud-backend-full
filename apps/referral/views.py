from django.db import transaction
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import permissions, status, views
from rest_framework.response import Response

from apps.referral.models import MarketInviteLink
from apps.referral.services import accept_store_invite, get_valid_invite
from apps.referral.serializers.user import (
    MarketInviteCreateSerializer,
    MarketInviteSerializer,
    ReferralCreateSerializer,
    ReferralCreatedEnvelopeSerializer,
    ReferralListEnvelopeSerializer,
    ReferralListSerializer,
)
from apps.market.models import Market
from apps.core.permissions import IsAuthenticatedUser
from apps.users.models import User
from utils.response import ApiResponse


class ReferalCreateView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]
    throttle_scope = 'referral_create'

    @extend_schema(
        request=ReferralCreateSerializer,
        responses={
            200: ReferralCreatedEnvelopeSerializer,
            201: ReferralCreatedEnvelopeSerializer,
            400: OpenApiResponse(description='Invalid referral code.'),
            409: OpenApiResponse(description='A different code was already applied.'),
            429: OpenApiResponse(description='Referral attempt limit exceeded.'),
        },
    )
    @transaction.atomic
    def post(self, request):
        serializer = ReferralCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        referred_user = get_object_or_404(
            User.objects.select_for_update(),
            id=request.user.id,
        )
        code = serializer.validated_data['code']
        invite = get_valid_invite(code, for_update=True)
        if invite is None or invite.created_by_id == referred_user.id:
            return Response(
                ApiResponse(
                    success=False,
                    code=status.HTTP_400_BAD_REQUEST,
                    error='Invalid referral code.',
                ),
                status=status.HTTP_400_BAD_REQUEST,
            )
        access, _ = accept_store_invite(
            user=referred_user,
            invite=invite,
            allow_referral_attribution=False,
        )
        return Response(
            ApiResponse(
                success=True,
                code=status.HTTP_201_CREATED,
                data={
                    'id': str(access.id),
                    'market_id': str(access.market_id),
                    'business_id': access.market.business_id,
                },
            ),
            status=status.HTTP_201_CREATED,
        )


class ReferalListView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(responses={200: ReferralListEnvelopeSerializer})
    def get(self, request):
        user = get_object_or_404(
            User.objects.prefetch_related('referrals_made__referred_user'),
            id=request.user.id,
        )
        return Response(
            ApiResponse(
                success=True,
                code=status.HTTP_200_OK,
                data=ReferralListSerializer(user).data,
            )
        )


class MarketInviteCreateView(views.APIView):
    permission_classes = [IsAuthenticatedUser]

    @extend_schema(
        request=MarketInviteCreateSerializer,
        responses={201: MarketInviteSerializer},
        tags=['Store invitations'],
    )
    def post(self, request):
        serializer = MarketInviteCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        market_query = Market.objects.all()
        if not request.user.is_staff:
            market_query = market_query.filter(user=request.user)
        market = get_object_or_404(market_query, pk=serializer.validated_data['market_id'])
        if market.status != Market.PUBLISHED:
            return Response(
                {'detail': 'Only published stores can create share links.'},
                status=status.HTTP_409_CONFLICT,
            )
        invite = MarketInviteLink.objects.create(
            market=market,
            created_by=request.user,
            expires_at=serializer.validated_data.get('expires_at'),
        )
        return Response(MarketInviteSerializer(invite).data, status=status.HTTP_201_CREATED)


class MarketInviteResolveView(views.APIView):
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        responses={200: MarketInviteSerializer},
        tags=['Store invitations'],
    )
    def get(self, request, token):
        invite = get_valid_invite(token)
        if invite is None:
            return Response({'detail': 'Invitation is unavailable.'}, status=status.HTTP_404_NOT_FOUND)
        # The public landing page must not disclose store or product data before OTP.
        return Response({'invite_token': str(invite.token), 'requires_otp': True})
