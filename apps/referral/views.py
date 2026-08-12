from django.db import transaction
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import permissions, status, views
from rest_framework.response import Response

from apps.referral.models import Referral
from apps.referral.serializers.user import (
    ReferralCreateSerializer,
    ReferralCreatedEnvelopeSerializer,
    ReferralListEnvelopeSerializer,
    ReferralListSerializer,
)
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
        existing = Referral.objects.select_related('referred_by').filter(
            referred_user=referred_user
        ).first()
        if existing is not None:
            if (
                existing.referred_by is not None
                and existing.referred_by.mobile_number
                == serializer.validated_data['code']
            ):
                return Response(
                    ApiResponse(
                        success=True,
                        code=status.HTTP_200_OK,
                        data={'id': str(existing.id)},
                    )
                )
            return Response(
                ApiResponse(
                    success=False,
                    code=status.HTTP_409_CONFLICT,
                    error='A different referral code was already applied.',
                ),
                status=status.HTTP_409_CONFLICT,
            )
        try:
            referrer = User.objects.get(
                mobile_number=serializer.validated_data['code']
            )
        except User.DoesNotExist:
            return Response(
                ApiResponse(
                    success=False,
                    code=status.HTTP_400_BAD_REQUEST,
                    error='Invalid referral code.',
                ),
                status=status.HTTP_400_BAD_REQUEST,
            )
        if referrer == referred_user:
            return Response(
                ApiResponse(
                    success=False,
                    code=status.HTTP_400_BAD_REQUEST,
                    error='Invalid referral code.',
                ),
                status=status.HTTP_400_BAD_REQUEST,
            )
        referral = Referral.objects.create(
            referred_by=referrer,
            referred_user=referred_user,
        )
        return Response(
            ApiResponse(
                success=True,
                code=status.HTTP_201_CREATED,
                data={'id': str(referral.id)},
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
