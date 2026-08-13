"""
Enhanced Views for ASOUD Platform
"""

import logging
from django.conf import settings
from django.core.cache import cache
from django.db import connection
from django.http import JsonResponse
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.views import APIView

logger = logging.getLogger(__name__)


class ErrorStatusSerializer(serializers.Serializer):
    error = serializers.CharField()
    message = serializers.CharField()
    code = serializers.CharField()


class DependencyStatusSerializer(serializers.Serializer):
    status = serializers.CharField()


class RateLimitStatusSerializer(serializers.Serializer):
    enabled = serializers.BooleanField()
    backend = serializers.CharField()
    configured_scopes = serializers.ListField(child=serializers.CharField())


class ApiIndexSerializer(serializers.Serializer):
    name = serializers.CharField()
    version = serializers.CharField()
    status = serializers.CharField()


class SecurityAuditSerializer(serializers.Serializer):
    security_status = serializers.CharField()
    csrf_protection = serializers.CharField()
    rate_limiting = serializers.CharField()
    websocket_query_tokens = serializers.CharField()
    timestamp = serializers.DateTimeField()

class CSRFFailureView(APIView):
    """
    Enhanced CSRF failure view with proper logging and security
    """
    serializer_class = ErrorStatusSerializer

    def post(self, request):
        """Handle CSRF failure for POST requests"""
        logger.warning(
            f"CSRF failure detected: IP={request.META.get('REMOTE_ADDR')}, "
            f"User-Agent={request.META.get('HTTP_USER_AGENT')}, "
            f"Path={request.path}"
        )
        
        return Response(
            {
                'error': 'CSRF verification failed',
                'message': 'Invalid or missing CSRF token',
                'code': 'CSRF_FAILURE'
            },
            status=status.HTTP_403_FORBIDDEN
        )
    
    def get(self, request):
        """Handle CSRF failure for GET requests"""
        logger.warning(
            f"CSRF failure detected: IP={request.META.get('REMOTE_ADDR')}, "
            f"User-Agent={request.META.get('HTTP_USER_AGENT')}, "
            f"Path={request.path}"
        )
        
        return Response(
            {
                'error': 'CSRF verification failed',
                'message': 'Invalid or missing CSRF token',
                'code': 'CSRF_FAILURE'
            },
            status=status.HTTP_403_FORBIDDEN
        )

class SecurityHeadersView(APIView):
    """
    View to add security headers to responses
    """
    
    def dispatch(self, request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        
        # Add security headers
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
        
        # HSTS header for HTTPS requests
        if request.is_secure():
            response['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains; preload'
        
        return response

class RateLimitView(APIView):
    """Staff-only, non-sensitive status for the real throttle control."""

    permission_classes = [IsAdminUser]
    throttle_classes = []
    serializer_class = RateLimitStatusSerializer

    def get(self, request):
        return Response(
            {
                "enabled": bool(settings.ASOUD_RATE_LIMIT_ENABLED),
                "backend": "redis_atomic",
                "configured_scopes": sorted(settings.ASOUD_RATE_LIMITS),
            }
        )


class LivenessView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = []
    serializer_class = DependencyStatusSerializer

    def get(self, request):
        return Response({"status": "ok"}, status=status.HTTP_200_OK)


def _dependencies_ready():
    probe_key = "readiness:v1"
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        cache.set(probe_key, "ok", 5)
        ready = cache.get(probe_key) == "ok"
        cache.delete(probe_key)
        return ready
    except Exception as exc:
        logger.warning(
            "Readiness dependency check failed (%s)", exc.__class__.__name__
        )
        return False


class ReadinessView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = []
    serializer_class = DependencyStatusSerializer

    def get(self, request):
        if _dependencies_ready():
            return Response({"status": "ready"}, status=status.HTTP_200_OK)
        return Response(
            {"status": "not_ready"},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )


class HealthCheckView(ReadinessView):
    """Compatibility alias retained for existing Docker and proxy probes."""

class ApiIndexView(APIView):
    """
    Public API index endpoint; returns 200 without authentication.
    """
    permission_classes = [AllowAny]
    authentication_classes = []
    serializer_class = ApiIndexSerializer

    def get(self, request):
        return Response({
            "name": "Asoud API",
            "version": "v1",
            "status": "available",
        }, status=status.HTTP_200_OK)

class SecurityAuditView(APIView):
    """Staff-only truthful status; never returns raw configuration values."""

    permission_classes = [IsAdminUser]
    throttle_classes = []
    serializer_class = SecurityAuditSerializer
    
    def get(self, request):
        """Return security audit information"""
        return Response({
            'security_status': 'active',
            'csrf_protection': 'enabled',
            'rate_limiting': (
                'enabled' if settings.ASOUD_RATE_LIMIT_ENABLED else 'disabled'
            ),
            'websocket_query_tokens': 'rejected',
            'timestamp': self.get_timestamp()
        })
    
    def get_timestamp(self):
        """Get current timestamp"""
        from django.utils import timezone
        return timezone.now().isoformat()

# Function-based views for compatibility
def csrf_failure_view(request, reason=""):
    """CSRF failure view function"""
    logger.warning(
        f"CSRF failure: {reason}, IP={request.META.get('REMOTE_ADDR')}, "
        f"Path={request.path}"
    )
    
    return JsonResponse(
        {
            'error': 'CSRF verification failed',
            'message': 'Invalid or missing CSRF token',
            'code': 'CSRF_FAILURE'
        },
        status=403
    )

def rate_limit_view(request):
    """Rate limit view function"""
    return JsonResponse(
        {
            'error': 'Rate limit exceeded',
            'message': 'Too many requests. Please try again later.',
            'code': 'RATE_LIMIT_EXCEEDED'
        },
        status=429
    )

