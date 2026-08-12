"""Production-only settings.

Secrets are accepted either as ``NAME`` or ``NAME_FILE``.  The latter is the
preferred path for Docker/Swarm/Kubernetes secrets.  This module deliberately
does not load repository ``.env`` files.
"""

import os
from pathlib import Path
from urllib.parse import quote

from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F403


def _secret(name, *, required=False, default=None):
    """Read a secret without ever including its value or path in errors."""
    value = os.environ.get(name)
    file_name = os.environ.get(f"{name}_FILE")
    if value and file_name:
        raise ImproperlyConfigured(f"Set only one of {name} or {name}_FILE.")
    if file_name:
        try:
            value = Path(file_name).read_text(encoding="utf-8").strip()
        except OSError as exc:
            raise ImproperlyConfigured(
                f"Unable to read the configured file for {name}."
            ) from exc
    if not value:
        value = default
    if required and not value:
        raise ImproperlyConfigured(f"{name} or {name}_FILE is required.")
    return value


def _csv(name, default=""):
    return [item.strip() for item in os.environ.get(name, default).split(",") if item.strip()]


DEBUG = False
ANALYTICS_ENABLED = True
ASOUD_RATE_LIMIT_ENABLED = True

SECRET_KEY = _secret("DJANGO_SECRET_KEY", required=True)
ASOUD_RATE_LIMIT_KEY_SECRET = _secret(
    "ASOUD_RATE_LIMIT_KEY_SECRET",
    default=SECRET_KEY,
)

ALLOWED_HOSTS = _csv("DJANGO_ALLOWED_HOSTS")
if not ALLOWED_HOSTS:
    raise ImproperlyConfigured("DJANGO_ALLOWED_HOSTS is required in production.")

database_name = os.environ.get("DATABASE_NAME")
database_user = os.environ.get("DATABASE_USERNAME")
database_host = os.environ.get("DATABASE_HOST")
if not all((database_name, database_user, database_host)):
    raise ImproperlyConfigured(
        "DATABASE_NAME, DATABASE_USERNAME and DATABASE_HOST are required."
    )

DATABASES = {  # noqa: F405
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": database_name,
        "USER": database_user,
        "PASSWORD": _secret("DATABASE_PASSWORD", required=True),
        "HOST": database_host,
        "PORT": os.environ.get("DATABASE_PORT", "5432"),
        "CONN_MAX_AGE": int(os.environ.get("DATABASE_CONN_MAX_AGE", "60")),
        "CONN_HEALTH_CHECKS": True,
        "OPTIONS": {
            "connect_timeout": 10,
            "options": "-c statement_timeout=30000",
            "sslmode": os.environ.get("DATABASE_SSLMODE", "require"),
        },
    }
}

REDIS_URL = _secret("REDIS_URL")
if not REDIS_URL:
    redis_host = os.environ.get("REDIS_HOST")
    if not redis_host:
        raise ImproperlyConfigured("REDIS_URL or REDIS_HOST is required.")
    redis_port = os.environ.get("REDIS_PORT", "6379")
    redis_username = os.environ.get("REDIS_USERNAME", "")
    redis_password = _secret("REDIS_PASSWORD", required=True)
    credentials = quote(redis_password, safe="")
    if redis_username:
        credentials = f"{quote(redis_username, safe='')}:{credentials}"
    else:
        credentials = f":{credentials}"
    REDIS_URL = f"rediss://{credentials}@{redis_host}:{redis_port}/0"

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": REDIS_URL,
        "KEY_PREFIX": "asoud",
        "TIMEOUT": 300,
        "OPTIONS": {
            "socket_connect_timeout": 5,
            "socket_timeout": 5,
        },
    }
}
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {"hosts": [REDIS_URL]},
    }
}

SMS_API = _secret("SMS_API", default="")
ZARINPAL_MERCHANT_ID = _secret("ZARINPAL_MERCHANT_ID", default="")

CSRF_TRUSTED_ORIGINS = _csv(
    "CSRF_TRUSTED_ORIGINS",
    "https://asoud.ir,https://www.asoud.ir,https://api.asoud.ir",
)
CORS_ALLOWED_ORIGINS = _csv(
    "CORS_ALLOWED_ORIGINS",
    "https://asoud.ir,https://www.asoud.ir,https://app.asoud.ir",
)

CSRF_COOKIE_SECURE = True
CSRF_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_AGE = 3600
CSRF_FAILURE_VIEW = "config.views.csrf_failure_view"

SESSION_COOKIE_SECURE = True
SESSION_COOKIE_SAMESITE = "Strict"
SESSION_COOKIE_HTTPONLY = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_COOKIE_AGE = 3600
SESSION_SAVE_EVERY_REQUEST = True

SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_HSTS_SECONDS = 31536000
SECURE_REDIRECT_EXEMPT = [
    r"^livez/?$",
    r"^readyz/?$",
    r"^health/?$",
    r"^api/v1/health/?$",
]
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"

STATIC_ROOT = os.environ.get("DJANGO_STATIC_ROOT", "/app/staticfiles")
STATICFILES_DIRS = []
MEDIA_ROOT = os.environ.get("DJANGO_MEDIA_ROOT", "/app/media")

WHITENOISE_USE_FINDERS = False
WHITENOISE_AUTOREFRESH = False
WHITENOISE_MANIFEST_STRICT = True
