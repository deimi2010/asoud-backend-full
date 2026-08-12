"""
Enhanced Exception Handler for ASOUD Platform
"""

import logging
import traceback
from django.http import JsonResponse
from django.core.exceptions import ValidationError, PermissionDenied
from django.db import DatabaseError, IntegrityError
from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler
from rest_framework.exceptions import (
    APIException, AuthenticationFailed, PermissionDenied as DRFPermissionDenied,
    NotAuthenticated, NotFound, MethodNotAllowed, NotAcceptable,
    UnsupportedMediaType, Throttled, ValidationError as DRFValidationError
)

from apps.core.rate_limit import RateLimitBackendUnavailable
from apps.core.request_identity import get_client_ip

logger = logging.getLogger(__name__)

class SecurityException(APIException):
    """Security-related exception"""
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = _('Security violation detected.')
    default_code = 'security_violation'

class RateLimitException(APIException):
    """Rate limit exception"""
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    default_detail = _('Rate limit exceeded.')
    default_code = 'rate_limit_exceeded'

class BusinessLogicException(APIException):
    """Business logic exception"""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _('Business logic violation.')
    default_code = 'business_logic_violation'

class InventoryException(APIException):
    """Inventory-related exception"""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _('Inventory operation failed.')
    default_code = 'inventory_error'

class PaymentException(APIException):
    """Payment-related exception"""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _('Payment operation failed.')
    default_code = 'payment_error'

def custom_exception_handler(exc, context):
    """
    Custom exception handler with enhanced logging and security
    """
    # Get the standard error response
    response = exception_handler(exc, context)
    
    if response is not None:
        # Get request information
        request = context.get('request')
        view = context.get('view')
        
        # Log the exception
        log_exception(exc, request, view, response)
        
        # Fix JSON serialization issues
        if isinstance(response.data, dict):
            response.data = dict(response.data)
        
        # Enhance error response
        custom_response_data = enhance_error_response(exc, response.data, request)
        
        # Create new response with enhanced data
        response.data = custom_response_data
        
        # Add security headers
        add_security_headers(response)
    
    return response

def log_exception(exc, request, view, response):
    """Log exception with context"""
    try:
        # Get request information
        user = getattr(request, 'user', None)
        user_id = user.id if user and hasattr(user, 'id') else None
        ip_address = get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        path = request.path
        method = request.method
        
        # Log based on exception type
        if isinstance(exc, (RateLimitException, Throttled)):
            logger.warning(
                "Rate limit exceeded: User=%s, Path=%s", user_id, path
            )
        elif isinstance(exc, RateLimitBackendUnavailable):
            logger.error("Rate limit backend unavailable: Path=%s", path)
        elif isinstance(exc, SecurityException):
            logger.warning(
                f"Security exception: {exc.detail}, "
                f"User={user_id}, IP={ip_address}, Path={path}, Method={method}"
            )
        elif isinstance(exc, (AuthenticationFailed, NotAuthenticated)):
            logger.warning(
                f"Authentication failed: User={user_id}, IP={ip_address}, Path={path}"
            )
        elif isinstance(exc, (PermissionDenied, DRFPermissionDenied)):
            logger.warning(
                f"Permission denied: User={user_id}, IP={ip_address}, Path={path}"
            )
        elif isinstance(exc, (DatabaseError, IntegrityError)):
            logger.error(
                f"Database error: {exc}, User={user_id}, IP={ip_address}, Path={path}"
            )
        elif isinstance(exc, (ValidationError, DRFValidationError)):
            logger.info(
                f"Validation error: {exc.detail if hasattr(exc, 'detail') else exc}, "
                f"User={user_id}, IP={ip_address}, Path={path}"
            )
        else:
            logger.error(
                f"Unhandled exception: {exc}, User={user_id}, IP={ip_address}, Path={path}, "
                f"Traceback: {traceback.format_exc()}"
            )
            
    except Exception as e:
        logger.error(f"Error in exception logging: {e}")

def enhance_error_response(exc, response_data, request):
    """Enhance error response with additional information"""
    try:
        # Base error structure
        enhanced_data = {
            'error': True,
            'timestamp': get_timestamp(),
            'path': request.path,
            'method': request.method,
        }
        
        # Add error details based on exception type
        if isinstance(exc, Throttled):
            parser_context = getattr(request, "parser_context", None) or {}
            scope = getattr(
                parser_context.get("view"),
                "_asoud_rate_limit_scope",
                None,
            )
            enhanced_data.update({
                'code': 'RATE_LIMITED',
                'message': 'Too many requests.',
                'retry_after': max(1, int(exc.wait or 1)),
            })
            if scope:
                enhanced_data['scope'] = scope
        elif isinstance(exc, RateLimitBackendUnavailable):
            enhanced_data.update({
                'code': 'RATE_LIMIT_UNAVAILABLE',
                'message': 'Request safety service is unavailable.',
            })
        elif isinstance(exc, SecurityException):
            enhanced_data.update({
                'code': 'SECURITY_VIOLATION',
                'message': 'Security violation detected',
                'details': str(exc.detail) if hasattr(exc, 'detail') else str(exc),
                'severity': 'high'
            })
        elif isinstance(exc, RateLimitException):
            enhanced_data.update({
                'code': 'RATE_LIMIT_EXCEEDED',
                'message': 'Rate limit exceeded',
                'details': 'Too many requests. Please try again later.',
                'retry_after': 60  # seconds
            })
        elif isinstance(exc, (AuthenticationFailed, NotAuthenticated)):
            enhanced_data.update({
                'code': 'AUTHENTICATION_FAILED',
                'message': 'Authentication failed',
                'details': 'Invalid or missing authentication credentials.',
                'severity': 'medium'
            })
        elif isinstance(exc, (PermissionDenied, DRFPermissionDenied)):
            enhanced_data.update({
                'code': 'PERMISSION_DENIED',
                'message': 'Permission denied',
                'details': 'You do not have permission to perform this action.',
                'severity': 'medium'
            })
        elif isinstance(exc, (DatabaseError, IntegrityError)):
            enhanced_data.update({
                'code': 'DATABASE_ERROR',
                'message': 'Database error',
                'details': 'An internal database error occurred.',
                'severity': 'high'
            })
        elif isinstance(exc, (ValidationError, DRFValidationError)):
            enhanced_data.update({
                'code': 'VALIDATION_ERROR',
                'message': 'Validation failed',
                'details': exc.detail if hasattr(exc, 'detail') else str(exc),
                'severity': 'low'
            })
        elif isinstance(exc, NotFound):
            enhanced_data.update({
                'code': 'NOT_FOUND',
                'message': 'Resource not found',
                'details': 'The requested resource was not found.',
                'severity': 'low'
            })
        elif isinstance(exc, MethodNotAllowed):
            enhanced_data.update({
                'code': 'METHOD_NOT_ALLOWED',
                'message': 'Method not allowed',
                'details': f'The {request.method} method is not allowed for this endpoint.',
                'severity': 'low'
            })
        else:
            enhanced_data.update({
                'code': 'INTERNAL_SERVER_ERROR',
                'message': 'Internal server error',
                'details': 'An unexpected error occurred.',
                'severity': 'high'
            })
        
        # Add original response data if available
        if response_data:
            enhanced_data['original_error'] = response_data
        
        return enhanced_data
        
    except Exception as e:
        logger.error(f"Error enhancing error response: {e}")
        return {
            'error': True,
            'code': 'ERROR_ENHANCEMENT_FAILED',
            'message': 'An error occurred while processing the error response',
            'details': str(e)
        }

def add_security_headers(response):
    """Add security headers to error response"""
    try:
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    except Exception as e:
        logger.error(f"Error adding security headers: {e}")

def get_timestamp():
    """Get current timestamp"""
    from django.utils import timezone
    return timezone.now().isoformat()

class ErrorHandler:
    """
    Centralized error handling utility
    """
    
    @staticmethod
    def handle_validation_error(field, message, code='validation_error'):
        """Handle validation error"""
        raise DRFValidationError({field: [message]})
    
    @staticmethod
    def handle_permission_error(message='Permission denied', code='permission_denied'):
        """Handle permission error"""
        raise DRFPermissionDenied(message)
    
    @staticmethod
    def handle_authentication_error(message='Authentication required', code='authentication_required'):
        """Handle authentication error"""
        raise AuthenticationFailed(message)
    
    @staticmethod
    def handle_security_error(message='Security violation', code='security_violation'):
        """Handle security error"""
        raise SecurityException(message)
    
    @staticmethod
    def handle_rate_limit_error(message='Rate limit exceeded', code='rate_limit_exceeded'):
        """Handle rate limit error"""
        raise RateLimitException(message)
    
    @staticmethod
    def handle_business_logic_error(message='Business logic violation', code='business_logic_violation'):
        """Handle business logic error"""
        raise BusinessLogicException(message)
    
    @staticmethod
    def handle_inventory_error(message='Inventory operation failed', code='inventory_error'):
        """Handle inventory error"""
        raise InventoryException(message)
    
    @staticmethod
    def handle_payment_error(message='Payment operation failed', code='payment_error'):
        """Handle payment error"""
        raise PaymentException(message)
    
    @staticmethod
    def handle_database_error(message='Database operation failed', code='database_error'):
        """Handle database error"""
        raise DatabaseError(message)
    
    @staticmethod
    def handle_integrity_error(message='Data integrity violation', code='integrity_error'):
        """Handle integrity error"""
        raise IntegrityError(message)
    
    @staticmethod
    def log_error(error, context=None):
        """Log error with context"""
        try:
            if context:
                logger.error(f"Error: {error}, Context: {context}")
            else:
                logger.error(f"Error: {error}")
        except Exception as e:
            logger.error(f"Error in error logging: {e}")
    
    @staticmethod
    def create_error_response(message, code, status_code=status.HTTP_400_BAD_REQUEST, details=None):
        """Create standardized error response"""
        return Response(
            {
                'error': True,
                'code': code,
                'message': message,
                'details': details,
                'timestamp': get_timestamp()
            },
            status=status_code
        )



