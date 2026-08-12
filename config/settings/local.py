"""Docker-local settings backed exclusively by PostgreSQL and Redis."""

import os
import secrets

from .base import *  # noqa: F401,F403


DEBUG = True
ENVIRONMENT = "local"


class DisableMigrations(dict):
    """Build a disposable local schema from current models without baselining prod."""

    def __contains__(self, item):
        return True

    def __getitem__(self, item):
        return None


MIGRATION_MODULES = DisableMigrations()

# A process-local signing key keeps `docker compose up` one-command for local
# development. Deployments must inject DJANGO_SECRET_KEY explicitly.
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY") or secrets.token_urlsafe(50)

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "backend", "frontend"]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("DATABASE_NAME", "asoud_dev"),
        "USER": os.environ.get("DATABASE_USERNAME", "asoud"),
        "PASSWORD": os.environ.get("DATABASE_PASSWORD", ""),
        "HOST": os.environ.get("DATABASE_HOST", "db"),
        "PORT": os.environ.get("DATABASE_PORT", "5432"),
        "CONN_MAX_AGE": 60,
        "CONN_HEALTH_CHECKS": True,
        "OPTIONS": {"connect_timeout": 10},
    }
}

REDIS_HOST = os.environ.get("REDIS_HOST", "redis")
REDIS_PORT = os.environ.get("REDIS_PORT", "6379")
REDIS_DB = os.environ.get("REDIS_DB", "0")
REDIS_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": REDIS_URL,
        "KEY_PREFIX": "asoud-local",
        "TIMEOUT": 300,
    }
}

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {"hosts": [REDIS_URL]},
    }
}

# OTP must fail closed when Redis is unavailable. The explicit SMS mock only
# acknowledges delivery in DEBUG and never logs or returns the generated code.
OTP_ALLOW_LOCAL_CACHE = False
SMS_MOCK_SEND = True
ANALYTICS_ENABLED = True
ANALYTICS_MODEL_DIR = BASE_DIR / 'ml_artifacts'  # noqa: F405

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

CORS_ALLOWED_ORIGINS = [
    "http://localhost:8080",
    "http://127.0.0.1:8080",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]
CORS_ALLOW_ALL_ORIGINS = False
CSRF_TRUSTED_ORIGINS = CORS_ALLOWED_ORIGINS

SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_SSL_REDIRECT = False

STATIC_ROOT = BASE_DIR / "staticfiles"  # noqa: F405
MEDIA_ROOT = BASE_DIR / "media"  # noqa: F405
