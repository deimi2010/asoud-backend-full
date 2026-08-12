from apps.wallet.models import Wallet, Transaction
from django.db import transaction
from django.db.models import F
from apps.users.models import User
from uuid import UUID
import logging

from apps.core.money import MAX_MONEY, normalize_money

logger = logging.getLogger(__name__)
MAX_TRANSACTION_AMOUNT = MAX_MONEY


class WalletCore:

    @staticmethod
    def _normalize_amount(amount):
        return normalize_money(amount)

    @staticmethod
    def _normalize_uuid(value):
        try:
            return value if isinstance(value, UUID) else UUID(str(value))
        except (TypeError, ValueError, AttributeError):
            return None

    @staticmethod
    def increase_balance(user: User, pk: str, amount):
        amount = WalletCore._normalize_amount(amount)
        wallet_id = WalletCore._normalize_uuid(pk)
        if amount is None or wallet_id is None:
            return False, "Invalid amount"
        
        try:
            with transaction.atomic():
                User.objects.select_for_update().get(id=user.id)
                wallet = Wallet.objects.select_for_update().get(id=wallet_id, user=user)
                wallet.balance = F('balance') + amount
                wallet.save(update_fields=['balance', 'updated_at'])
                wallet.refresh_from_db(fields=['balance'])
                
                logger.info('Wallet increased successfully')
                Transaction.objects.create(
                    user = user,
                    from_wallet = wallet,
                    to_wallet = wallet,
                    action = 'charge', 
                    amount = amount
                )
        except Wallet.DoesNotExist:
            return False, "Wallet not found"
        except Exception:
            logger.exception('Wallet increase failed')
            return False, "Wallet operation failed"

        return True, wallet.balance
    
    @staticmethod
    def decrease_balance(user: User, pk: str, amount):
        amount = WalletCore._normalize_amount(amount)
        wallet_id = WalletCore._normalize_uuid(pk)
        if amount is None or wallet_id is None:
            return False, "Invalid amount"
        
        try:
            with transaction.atomic():
                User.objects.select_for_update().get(id=user.id)
                wallet = Wallet.objects.select_for_update().get(id=wallet_id, user=user)
                if wallet.balance < amount:
                    return False, "Insufficient Balance"
                wallet.balance = F('balance') - amount
                wallet.save(update_fields=['balance', 'updated_at'])
                wallet.refresh_from_db(fields=['balance'])
                
                Transaction.objects.create(
                    user = user,
                    from_wallet = wallet,
                    to_wallet = wallet,
                    action = 'spend', 
                    amount = amount
                )
        except Wallet.DoesNotExist:
            return False, "Wallet not found"
        except Exception:
            logger.exception('Wallet decrease failed')
            return False, "Wallet operation failed"
        
        return True, wallet.balance
    
    @staticmethod
    def transaction(user: User, from_pk: str, to_pk: str, amount):
        amount = WalletCore._normalize_amount(amount)
        from_id = WalletCore._normalize_uuid(from_pk)
        to_id = WalletCore._normalize_uuid(to_pk)
        if amount is None or from_id is None or to_id is None:
            return False, "Invalid amount"
        if from_id == to_id:
            return False, "Source and destination wallets must differ"
        
        try:
            with transaction.atomic():
                User.objects.select_for_update().get(id=user.id)
                # Lock in UUID order to avoid deadlocks, then map by normalized UUID.
                locked_wallets = list(
                    Wallet.objects.select_for_update()
                    .filter(id__in=(from_id, to_id))
                    .order_by('id')
                )
                wallets_by_id = {wallet.id: wallet for wallet in locked_wallets}
                if len(wallets_by_id) != 2:
                    return False, "Wallet not found"

                from_wallet = wallets_by_id[from_id]
                to_wallet = wallets_by_id[to_id]
                if from_wallet.user_id != user.id:
                    return False, "Source wallet does not belong to user"

                if from_wallet.balance < amount:
                    return False, "Insufficient Balance"

                from_wallet.balance = F('balance') - amount
                to_wallet.balance = F('balance') + amount

                # Balance-only updates avoid rechecking unchanged owner FKs and
                # therefore avoid cross-user lock inversion on reverse transfers.
                from_wallet.save(update_fields=['balance', 'updated_at'])
                to_wallet.save(update_fields=['balance', 'updated_at'])

                from_wallet.refresh_from_db(fields=['balance'])
                to_wallet.refresh_from_db(fields=['balance'])

                Transaction.objects.create(
                    user = user,
                    from_wallet = from_wallet,
                    to_wallet = to_wallet,
                    action = 'exchange', 
                    amount = amount
                )
        except Exception:
            logger.exception('Wallet transfer failed')
            return False, "Wallet operation failed"
        
        return True, (from_wallet.balance, to_wallet.balance)

