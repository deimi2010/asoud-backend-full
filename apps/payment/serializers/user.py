from rest_framework import serializers
from django.contrib.contenttypes.models import ContentType
from apps.payment.models import Payment, Zarinpal
from apps.wallet.models import Wallet
from apps.wallet.serializer import WalletSerializer
from apps.advertise.models import Advertisement
from apps.advertise.serializers import AdvertiseSerializer
from apps.cart.models import Order
from apps.market.models import Market
from decimal import Decimal

from apps.core.money import MONEY_DECIMAL_PLACES, MONEY_MAX_DIGITS
from drf_spectacular.utils import extend_schema_field

class PaymentSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(read_only=True)
    target = serializers.SerializerMethodField()
    target_content = serializers.SerializerMethodField()

    class Meta:
        model = Payment
        fields = [
            'id',
            'amount',
            'target',
            'target_content',
            'status',
            'created_at',
        ]

    @extend_schema_field(serializers.DictField)
    def get_target(self, obj):
        target_model = obj.target_content_type.model_class()

        if target_model == Wallet:
            target = Wallet.objects.get(id=obj.target_id)
            return WalletSerializer(target).data
        
        elif target_model == Advertisement:
            target = Advertisement.objects.get(id=obj.target_id)
            return AdvertiseSerializer(target).data

        elif target_model == Order:
            return {'id': str(obj.target_id)}

        return {'id': str(obj.target_id)}

    @extend_schema_field(serializers.CharField)
    def get_target_content(self, obj):
        target_model = obj.target_content_type.model_class()

        if target_model == Wallet:
            return "wallet"
        
        elif target_model == Advertisement:
            return "advertisement"

        elif target_model == Order:
            return "order"

        return "unknown"
            
class PaymentDetailSerializer(serializers.ModelSerializer):
    target = serializers.SerializerMethodField()
    target_content = serializers.SerializerMethodField()
    gateway = serializers.SerializerMethodField()

    class Meta:
        model = Payment
        fields = [
            'id',
            'amount',
            'target',
            'target_id',
            'target_content',
            'gateway',
        ]

    @extend_schema_field(serializers.DictField)
    def get_target(self, obj):
        target_model = obj.target_content_type.model_class()

        if target_model == Wallet:
            target = Wallet.objects.get(id=obj.target_id)
            return WalletSerializer(target).data
        
        elif target_model == Advertisement:
            target = Advertisement.objects.get(id=obj.target_id)
            return AdvertiseSerializer(target).data

        elif target_model == Order:
            return {'id': str(obj.target_id)}

        return {'id': str(obj.target_id)}
    
    @extend_schema_field(serializers.DictField)
    def get_gateway(self, obj):
        gateway_model = obj.gateway_content_type.model_class()
        if gateway_model == Zarinpal:
            return {
                'id' : obj.gateway_id,
                'name': 'zarinpal'
            }
        else:
            return {
                'name': 'none'
            }

    @extend_schema_field(serializers.CharField)
    def get_target_content(self, obj):
        target_model = obj.target_content_type.model_class()

        if target_model == Wallet:
            return "wallet"
        
        elif target_model == Advertisement:
            return "advertisement"

        elif target_model == Order:
            return "order"

        return "unknown"
        
class PaymentCreateSerializer(serializers.Serializer):
    amount = serializers.DecimalField(
        max_digits=MONEY_MAX_DIGITS,
        decimal_places=MONEY_DECIMAL_PLACES,
        min_value=Decimal('1'),
    )
    target = serializers.ChoiceField(choices=('wallet', 'order', 'market_subscription'))
    target_id = serializers.UUIDField()
    gateway = serializers.ChoiceField(choices=('zarinpal',))

    def validate_amount(self, value):
        if value != value.to_integral_value():
            raise serializers.ValidationError('Gateway amount must be a whole IRT value.')
        return value

    def validate(self, attrs):
        request = self.context.get('request')
        if request is None or not request.user.is_authenticated:
            raise serializers.ValidationError('Authenticated user is required.')

        user = request.user
        if attrs['target'] == 'wallet':
            try:
                target = Wallet.objects.get(id=attrs['target_id'], user=user)
            except Wallet.DoesNotExist:
                raise serializers.ValidationError({'target_id': 'Wallet not found.'})
            resolved_amount = attrs['amount']
        elif attrs['target'] == 'order':
            try:
                target = Order.objects.prefetch_related('items__product', 'items__affiliate').get(
                    id=attrs['target_id'],
                    user=user,
                    status__in=(Order.PENDING, Order.VERIFIED, Order.PROCESSING),
                    type=Order.ONLINE,
                    is_paid=False,
                )
            except Order.DoesNotExist:
                raise serializers.ValidationError({'target_id': 'Payable order not found.'})

            pending_payment = None
            if target.status == Order.PROCESSING:
                order_content_type = ContentType.objects.get_for_model(Order)
                pending_payment = Payment.objects.filter(
                    user=user,
                    target_content_type=order_content_type,
                    target_id=target.id,
                    status=Payment.PENDING,
                ).first()
                if pending_payment is None:
                    raise serializers.ValidationError(
                        {'target_id': 'Order payment requires reconciliation.'}
                    )

            if not target.items.exists():
                raise serializers.ValidationError({'target_id': 'Order has no items.'})
            resolved_amount = (
                Decimal(str(pending_payment.amount))
                if pending_payment is not None
                else Decimal(str(target.total_price()))
            )
            if resolved_amount <= 0:
                raise serializers.ValidationError({'target_id': 'Order total must be positive.'})
            if attrs['amount'] != resolved_amount:
                raise serializers.ValidationError({'amount': 'Amount does not match the current order total.'})

        else:
            try:
                target = Market.objects.select_related('sub_category').get(
                    id=attrs['target_id'],
                    user=user,
                    status__in=(Market.DRAFT, Market.QUEUE, Market.NOT_PUBLISHED, Market.NEEDS_EDITING),
                )
            except Market.DoesNotExist:
                raise serializers.ValidationError({'target_id': 'Publishable store not found.'})
            resolved_amount = Decimal(str(target.sub_category.market_fee))
            if resolved_amount <= 0:
                raise serializers.ValidationError({'amount': 'Store subscription fee is not configured.'})
            if attrs['amount'] != resolved_amount:
                raise serializers.ValidationError({'amount': 'Amount does not match the subscription fee.'})

        attrs['resolved_target'] = target
        attrs['resolved_amount'] = resolved_amount
        return attrs
