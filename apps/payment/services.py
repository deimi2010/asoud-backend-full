"""
Payment Service Layer

Encapsulates payment operations with consistent error handling, validation, and logging.
This service layer provides a clean interface for payment operations while maintaining
backward compatibility with existing PaymentCore.
"""

import logging
from decimal import Decimal
from typing import Tuple, Optional, Dict, Any

from django.db import transaction
from django.conf import settings

from apps.payment.core import PaymentCore, validate_payment_amount
from apps.payment.models import Payment, Zarinpal
from apps.cart.models import Order
from apps.wallet.models import Wallet
from apps.users.models import User


logger = logging.getLogger(__name__)


class PaymentService:
    """
    Handles payment operations with consistent error handling and logging.
    
    This service layer provides:
    - Payment creation with validation
    - Payment verification with proper state management
    - Comprehensive error handling
    - Audit logging
    - Transaction safety
    """
    
    def __init__(self):
        self.core = PaymentCore()
    
    def create_payment(self, user: User, target_type: str, target_id: str, amount: Decimal) -> Tuple[bool, Dict[str, Any]]:
        """
        Create a payment with comprehensive validation and error handling.
        
        Args:
            user: The user making the payment
            target_type: Type of payment target ('order' or 'wallet')
            target_id: ID of the payment target
            amount: Payment amount
            
        Returns:
            Tuple of (success, response_dict) where response_dict contains either:
            - {'gateway_id': str, 'authority': str} on success
            - {'error': str, 'code': str} on failure
        """
        # Validate user
        if not user or not user.is_authenticated:
            return False, {'error': 'User is not authenticated', 'code': 'auth_required'}
        
        # Validate target type
        if target_type not in ('order', 'wallet'):
            return False, {'error': f'Invalid target type: {target_type}', 'code': 'invalid_target'}
        
        # Validate amount
        is_valid, error_msg = validate_payment_amount(amount)
        if not is_valid:
            return False, {'error': error_msg, 'code': 'invalid_amount'}
        
        # Resolve target object
        try:
            if target_type == 'order':
                target = Order.objects.get(id=target_id, user=user)
            else:  # wallet
                target = Wallet.objects.get(id=target_id, user=user)
        except (Order.DoesNotExist, Wallet.DoesNotExist):
            error_msg = f'{target_type.title()} not found'
            logger.warning(f'Payment creation failed: {error_msg} for user {user.id}')
            return False, {'error': error_msg, 'code': f'{target_type}_not_found'}
        
        # Create payment using PaymentCore
        try:
            success, result = self.core.pay(
                user,
                {'resolved_target': target, 'resolved_amount': amount}
            )
            
            if success:
                gateway = result  # This is the Zarinpal object
                logger.info(
                    f'Payment created: user={user.id}, target_type={target_type}, '
                    f'target_id={target_id}, amount={amount}, gateway_id={gateway.id}'
                )
                return True, {
                    'gateway_id': str(gateway.id),
                    'authority': gateway.authority,
                    'payment_id': str(gateway.payment_id)
                }
            else:
                logger.warning(
                    f'Payment creation rejected: user={user.id}, target_type={target_type}, '
                    f'reason={result}'
                )
                return False, {'error': result, 'code': 'payment_rejected'}
        except Exception as exc:
            logger.exception(f'Payment creation exception for user {user.id}: {exc}')
            return False, {'error': 'Payment system error', 'code': 'system_error'}
    
    def verify_payment(self, authority: str, status_code: str = 'OK') -> Tuple[bool, Dict[str, Any]]:
        """
        Verify a payment with proper state management and logging.
        
        Args:
            authority: Payment authority from gateway
            status_code: Status from gateway (typically 'OK' for success)
            
        Returns:
            Tuple of (success, response_dict)
        """
        if not authority:
            return False, {'error': 'No authority provided', 'code': 'missing_authority'}
        
        try:
            # Create request-like object for PaymentCore.verify
            class Request:
                def __init__(self, authority, status):
                    self.GET = {'Authority': authority, 'Status': status}
            
            request = Request(authority, status_code)
            success, message = self.core.verify(request)
            
            if success:
                logger.info(f'Payment verified: authority={authority}')
                return True, {'message': message, 'code': 'verified'}
            else:
                logger.warning(f'Payment verification failed: authority={authority}, reason={message}')
                return False, {'error': message, 'code': 'verification_failed'}
        except Exception as exc:
            logger.exception(f'Payment verification exception for authority {authority}: {exc}')
            return False, {'error': 'Verification system error', 'code': 'system_error'}
    
    def get_payment_status(self, payment_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the current status of a payment.
        
        Args:
            payment_id: ID of the payment to check
            
        Returns:
            Dict with payment details or None if not found
        """
        try:
            payment = Payment.objects.select_related('zarinpal_data').get(id=payment_id)
            
            return {
                'id': str(payment.id),
                'status': payment.status,
                'amount': str(payment.amount),
                'created_at': payment.created_at.isoformat(),
                'updated_at': payment.updated_at.isoformat(),
                'gateway': {
                    'id': str(payment.zarinpal_data.id) if payment.zarinpal_data else None,
                    'authority': payment.zarinpal_data.authority if payment.zarinpal_data else None,
                    'transaction_id': payment.zarinpal_data.transaction_id if payment.zarinpal_data else None,
                }
            }
        except Payment.DoesNotExist:
            return None
        except Exception as exc:
            logger.exception(f'Error retrieving payment status for {payment_id}: {exc}')
            return None


# Singleton instance for consistent usage
payment_service = PaymentService()
