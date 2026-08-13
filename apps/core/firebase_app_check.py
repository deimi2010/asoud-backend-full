import logging

from django.conf import settings
from django.http import JsonResponse

from apps.notification.firebase import verify_app_check_token

logger = logging.getLogger(__name__)


class FirebaseAppCheckMiddleware:
    """Optionally enforce Firebase App Check on the versioned API."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not self._requires_app_check(request.path):
            return self.get_response(request)
        token = request.headers.get('X-Firebase-AppCheck')
        if not token:
            return self._rejected('app_check_token_missing')
        try:
            request.firebase_app = verify_app_check_token(token)
            if request.firebase_app is None:
                return self._rejected('app_check_not_configured')
        except Exception:
            logger.warning('Firebase App Check verification rejected a request')
            return self._rejected('app_check_token_invalid')
        return self.get_response(request)

    @staticmethod
    def _requires_app_check(path):
        return (
            settings.FIREBASE_APP_CHECK_ENFORCED
            and path.startswith('/api/v1/')
            and not any(path.startswith(item) for item in settings.FIREBASE_APP_CHECK_EXEMPT_PATHS)
        )

    @staticmethod
    def _rejected(code):
        return JsonResponse({'error': code}, status=401)
