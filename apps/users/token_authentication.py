from datetime import timedelta

from django.conf import settings
from django.utils import timezone
from rest_framework.authentication import TokenAuthentication
from rest_framework.exceptions import AuthenticationFailed


class ExpiringTokenAuthentication(TokenAuthentication):
    """DRF token authentication with a server-enforced maximum age."""

    def authenticate_credentials(self, key):
        user, token = super().authenticate_credentials(key)
        ttl_seconds = getattr(settings, 'ASOUD_TOKEN_TTL_SECONDS', 30 * 24 * 60 * 60)
        if token.created < timezone.now() - timedelta(seconds=ttl_seconds):
            token.delete()
            raise AuthenticationFailed('Token has expired.')
        return user, token
