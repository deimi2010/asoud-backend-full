from django.conf import settings
from django.http import JsonResponse


class RequestSizeLimitMiddleware:
    """Reject oversized bodies before Django REST Framework parses them."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        raw_length = request.META.get('CONTENT_LENGTH')
        try:
            content_length = int(raw_length) if raw_length else 0
        except (TypeError, ValueError):
            return JsonResponse({'detail': 'Invalid Content-Length'}, status=400)

        limit = settings.ASOUD_MAX_REQUEST_BODY_BYTES
        if content_length > limit:
            return JsonResponse({'detail': 'Request body too large'}, status=413)
        return self.get_response(request)
