"""CI settings: disposable current-model schema on real PostgreSQL and Redis."""

import os

# Keep PostgreSQL's native ArrayField implementation. The local test settings
# use a text shim only because their disposable database is SQLite.
os.environ["ASOUD_TEST_SQLITE_ARRAY_SHIM"] = "0"

from .test import *  # noqa: F401,F403


DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("DATABASE_NAME", "test_asoud"),
        "USER": os.getenv("DATABASE_USERNAME", "postgres"),
        "PASSWORD": os.getenv("DATABASE_PASSWORD", "postgres"),
        "HOST": os.getenv("DATABASE_HOST", "127.0.0.1"),
        "PORT": os.getenv("DATABASE_PORT", "5432"),
    }
}

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": os.getenv("REDIS_URL", "redis://127.0.0.1:6379/15"),
    }
}

OTP_ALLOW_LOCAL_CACHE = False
