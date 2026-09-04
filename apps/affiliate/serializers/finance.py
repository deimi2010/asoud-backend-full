from decimal import Decimal
from rest_framework import serializers

from apps.affiliate.models import AffiliateCommission, AffiliatePayout


class AffiliateCommissionSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='affiliate_product.name', read_only=True)
    order_id = serializers.UUIDField(source='order.id', read_only=True)

    class Meta:
        model = AffiliateCommission
        fields = (
            'id', 'order_id', 'product_name', 'quantity', 'customer_total',
            'seller_total', 'gross_commission', 'platform_fee',
            'marketer_total', 'status', 'available_at', 'created_at',
            'seller_status', 'seller_available_at',
        )


class AffiliatePayoutSerializer(serializers.ModelSerializer):
    class Meta:
        model = AffiliatePayout
        fields = ('id', 'amount', 'role', 'status', 'tracking_code', 'admin_note', 'paid_at', 'created_at')
        read_only_fields = fields


class AffiliatePayoutRequestSerializer(serializers.Serializer):
    amount = serializers.DecimalField(
        max_digits=14, decimal_places=3, min_value=Decimal('1'),
    )
    role = serializers.ChoiceField(
        choices=AffiliatePayout.ROLE_CHOICES,
        default=AffiliatePayout.MARKETER_ROLE,
    )
