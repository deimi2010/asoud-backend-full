from decimal import Decimal
from uuid import UUID

from django.test import TestCase

from apps.users.models import User
from apps.wallet.core import WalletCore
from apps.wallet.models import Transaction, Wallet


class WalletCoreSecurityTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('09120000001', None)
        self.other_user = User.objects.create_user('09120000002', None)

    def test_transfer_maps_string_uuid_to_the_real_source_wallet(self):
        source = Wallet.objects.create(
            id=UUID('00000000-0000-0000-0000-000000000001'),
            user=self.user,
            balance=100,
        )
        destination = Wallet.objects.create(
            id=UUID('00000000-0000-0000-0000-000000000002'),
            user=self.other_user,
            balance=10,
        )

        success, _ = WalletCore.transaction(
            self.user,
            str(source.id),
            str(destination.id),
            Decimal('25.000'),
        )

        self.assertTrue(success)
        source.refresh_from_db()
        destination.refresh_from_db()
        self.assertEqual(source.balance, 75)
        self.assertEqual(destination.balance, 35)
        transaction = Transaction.objects.get(action='exchange')
        self.assertEqual(transaction.from_wallet, source)
        self.assertEqual(transaction.to_wallet, destination)

    def test_transfer_rejects_a_source_wallet_owned_by_someone_else(self):
        foreign_source = Wallet.objects.create(user=self.other_user, balance=100)
        destination = Wallet.objects.create(user=self.user, balance=0)

        success, message = WalletCore.transaction(
            self.user,
            foreign_source.id,
            destination.id,
            25,
        )

        self.assertFalse(success)
        self.assertIn('does not belong', message)
        foreign_source.refresh_from_db()
        destination.refresh_from_db()
        self.assertEqual(foreign_source.balance, 100)
        self.assertEqual(destination.balance, 0)
        self.assertFalse(Transaction.objects.exists())

    def test_increase_and_decrease_reject_foreign_wallet(self):
        foreign_wallet = Wallet.objects.create(user=self.other_user, balance=100)

        increased, _ = WalletCore.increase_balance(self.user, foreign_wallet.id, 10)
        decreased, _ = WalletCore.decrease_balance(self.user, foreign_wallet.id, 10)

        self.assertFalse(increased)
        self.assertFalse(decreased)
        foreign_wallet.refresh_from_db()
        self.assertEqual(foreign_wallet.balance, 100)
        self.assertFalse(Transaction.objects.exists())

    def test_insufficient_balance_never_creates_a_transaction(self):
        source = Wallet.objects.create(user=self.user, balance=5)

        success, message = WalletCore.decrease_balance(self.user, source.id, 10)

        self.assertFalse(success)
        self.assertEqual(message, 'Insufficient Balance')
        source.refresh_from_db()
        self.assertEqual(source.balance, 5)
        self.assertFalse(Transaction.objects.exists())

    def test_self_transfer_is_rejected(self):
        wallet = Wallet.objects.create(user=self.user, balance=100)

        success, _ = WalletCore.transaction(self.user, wallet.id, wallet.id, 10)

        self.assertFalse(success)
        wallet.refresh_from_db()
        self.assertEqual(wallet.balance, 100)

    def test_amount_above_transaction_column_capacity_is_rejected(self):
        wallet = Wallet.objects.create(user=self.user, balance=0)

        success, _ = WalletCore.increase_balance(
            self.user,
            wallet.id,
            Decimal('1000000000000000000'),
        )

        self.assertFalse(success)
        wallet.refresh_from_db()
        self.assertEqual(wallet.balance, 0)
        self.assertFalse(Transaction.objects.exists())

    def test_fractional_irt_is_rejected_without_rounding(self):
        wallet = Wallet.objects.create(user=self.user, balance=10)

        success, _ = WalletCore.increase_balance(
            self.user,
            wallet.id,
            Decimal('1.5'),
        )

        self.assertFalse(success)
        wallet.refresh_from_db()
        self.assertEqual(wallet.balance, Decimal('10'))
        self.assertFalse(Transaction.objects.exists())

    def test_decimal_balance_is_exact_after_repeated_updates(self):
        wallet = Wallet.objects.create(user=self.user, balance=0)

        for _ in range(10):
            success, _ = WalletCore.increase_balance(self.user, wallet.id, 1)
            self.assertTrue(success)

        wallet.refresh_from_db()
        self.assertEqual(wallet.balance, Decimal('10'))
        self.assertEqual(
            sum(self.user.wallet_transactions.values_list('amount', flat=True)),
            Decimal('10'),
        )
