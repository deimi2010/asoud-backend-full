"""Fast, isolated settings for the Django test runner."""

import os

from .development import *  # noqa: F401,F403
from django.contrib.postgres.fields import ArrayField


# A few legacy models use PostgreSQL ArrayField while local tests use SQLite.
# These apps are outside most unit-test scopes, so a text column is sufficient
# for disposable schema creation until the migration baseline is reconciled.
if os.getenv('ASOUD_TEST_SQLITE_ARRAY_SHIM', '1') == '1':
    ArrayField.db_type = lambda self, connection: 'text'
ENVIRONMENT = 'test'
ANALYTICS_ENABLED = True
ASOUD_RATE_LIMIT_ENABLED = False


class DisableMigrations(dict):
    """Build the disposable test schema directly from current models."""

    def __contains__(self, item):
        return True

    def __getitem__(self, item):
        return None


MIGRATION_MODULES = DisableMigrations()
PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
MIDDLEWARE = [
    middleware
    for middleware in MIDDLEWARE  # noqa: F405
    if not middleware.startswith('whitenoise.')
]

LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'handlers': {'null': {'class': 'logging.NullHandler'}},
    'root': {'handlers': ['null'], 'level': 'CRITICAL'},
}
