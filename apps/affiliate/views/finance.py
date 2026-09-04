from decimal import Decimal

from django.db import transaction
from django.db.models import Sum
from rest_framework import permissions, serializers, status, views
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, inline_serializer

from apps.affiliate.models import AffiliateCommission, AffiliatePayout
from apps.affiliate.serializers.finance import (
    AffiliateCommissionSerializer,
    AffiliatePayoutRequestSerializer,
    AffiliatePayoutSerializer,
)
from apps.affiliate.services import release_due_commissions
from apps.users.models import UserProfile
from utils.response import ApiResponse


def _sum(queryset, field):
    return queryset.aggregate(value=Sum(field))['value'] or Decimal('0')


class AffiliateFinanceView(views.APIView):
    permission_classes = (permissions.IsAuthenticated,)

    @extend_schema(
        responses=inline_serializer(
            name='AffiliateFinanceDashboard',
            fields={
                'marketer': serializers.DictField(),
                'seller': serializers.DictField(),
                'recent': AffiliateCommissionSerializer(many=True),
                'payouts': AffiliatePayoutSerializer(many=True),
            },
        ),
        tags=['Affiliate - Finance'],
    )
    def get(self, request):
        release_due_commissions(request.user)
        earnings = AffiliateCommission.objects.filter(marketer=request.user)
        sales = AffiliateCommission.objects.filter(seller=request.user)
        return Response(ApiResponse(success=True, code=200, data={
            'marketer': {
                'held': _sum(earnings.filter(status=AffiliateCommission.HELD), 'marketer_total'),
                'available': _sum(earnings.filter(status=AffiliateCommission.AVAILABLE), 'marketer_total'),
                'paid': _sum(earnings.filter(status=AffiliateCommission.PAID), 'marketer_total'),
                'gross_sales': _sum(earnings.exclude(status=AffiliateCommission.REVERSED), 'customer_total'),
            },
            'seller': {
                'held': _sum(sales.filter(seller_status=AffiliateCommission.HELD), 'seller_total'),
                'available': _sum(sales.filter(seller_status=AffiliateCommission.AVAILABLE), 'seller_total'),
                'paid': _sum(sales.filter(seller_status=AffiliateCommission.PAID), 'seller_total'),
                'gross_sales': _sum(sales.exclude(seller_status=AffiliateCommission.REVERSED), 'customer_total'),
            },
            'recent': AffiliateCommissionSerializer(
                earnings.select_related('affiliate_product', 'order')[:50], many=True,
            ).data,
            'payouts': AffiliatePayoutSerializer(
                request.user.affiliate_payouts.all()[:50], many=True,
            ).data,
        }))


class AffiliatePayoutRequestView(views.APIView):
    permission_classes = (permissions.IsAuthenticated,)

    @extend_schema(
        request=AffiliatePayoutRequestSerializer,
        responses={201: AffiliatePayoutSerializer},
        tags=['Affiliate - Finance'],
    )
    @transaction.atomic
    def post(self, request):
        serializer = AffiliatePayoutRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            profile = UserProfile.objects.select_for_update().get(
                user=request.user,
                status=UserProfile.APPROVED,
            )
        except UserProfile.DoesNotExist:
            return Response(
                ApiResponse(success=False, code=403, error='Approved identity profile is required'),
                status=status.HTTP_403_FORBIDDEN,
            )
        if not profile.iban_number:
            return Response(
                ApiResponse(success=False, code=400, error='Verified IBAN is required'),
                status=status.HTTP_400_BAD_REQUEST,
            )
        release_due_commissions(request.user)
        requested = serializer.validated_data['amount']
        role = serializer.validated_data['role']
        owner_field = 'marketer' if role == AffiliatePayout.MARKETER_ROLE else 'seller'
        status_field = 'status' if role == AffiliatePayout.MARKETER_ROLE else 'seller_status'
        amount_field = 'marketer_total' if role == AffiliatePayout.MARKETER_ROLE else 'seller_total'
        available = AffiliateCommission.objects.select_for_update().filter(
            **{
                owner_field: request.user,
                status_field: AffiliateCommission.AVAILABLE,
            }
        ).exclude(payouts__role=role).order_by('created_at')
        selected = []
        total = Decimal('0')
        for row in available:
            row_amount = getattr(row, amount_field)
            if total + row_amount > requested:
                continue
            selected.append(row)
            total += row_amount
            if total == requested:
                break
        if total != requested:
            return Response(
                ApiResponse(
                    success=False,
                    code=400,
                    error='Request the exact sum of one or more available commissions',
                ),
                status=status.HTTP_400_BAD_REQUEST,
            )
        payout = AffiliatePayout.objects.create(
            marketer=request.user, amount=total, role=role,
        )
        payout.commissions.set(selected)
        return Response(
            ApiResponse(
                success=True, code=201,
                data=AffiliatePayoutSerializer(payout).data,
                message='Payout request submitted',
            ),
            status=status.HTTP_201_CREATED,
        )
