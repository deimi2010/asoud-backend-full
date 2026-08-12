from rest_framework import serializers
from apps.wallet.models import Wallet, Transaction
from decimal import Decimal

from apps.core.money import MONEY_DECIMAL_PLACES, MONEY_MAX_DIGITS


class WalletCheckSerializer(serializers.Serializer):
    amount = serializers.DecimalField(
        max_digits=MONEY_MAX_DIGITS,
        decimal_places=MONEY_DECIMAL_PLACES,
        min_value=Decimal('1'),
    )

class WalletSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(read_only=True)
    class Meta:
        model = Wallet
        fields = [
            'id',
            'balance',
        ]

class WalletPaySerializer(serializers.Serializer):
    amount = serializers.DecimalField(
        max_digits=MONEY_MAX_DIGITS,
        decimal_places=MONEY_DECIMAL_PLACES,
        min_value=Decimal('1'),
    )
    target_id = serializers.UUIDField()
    target_content = serializers.ChoiceField(choices=('order', 'wallet'))


class TransactionSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(read_only=True)
    from_wallet = WalletSerializer()
    to_wallet = WalletSerializer()
    class Meta:
        model = Transaction
        fields = [
            'id',
            'from_wallet',
            'to_wallet',
            'action',
            'amount',
            'created_at',
        ]
