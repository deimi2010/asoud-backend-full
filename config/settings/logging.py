"""Logging configuration shared by all environments."""

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {'format': '{levelname} {message}', 'style': '{'},
        'detailed': {
            'format': '{levelname} {asctime} {name} {module} {funcName} {lineno:d} {message}',
            'style': '{',
        },
        'security': {
            'format': 'SECURITY {levelname} {asctime} {name} {module} {funcName} {lineno:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'level': 'INFO',
            'formatter': 'simple',
            'stream': 'ext://sys.stdout',
        },
    },
    'loggers': {
        name: {
            'handlers': ['console'],
            'level': level,
            'propagate': False,
        }
        for name, level in {
            'django': 'INFO',
            'django.request': 'WARNING',
            'django.security': 'WARNING',
            'config.security': 'WARNING',
            'apps.core': 'INFO',
            'apps.users': 'INFO',
            'apps.payment': 'INFO',
        }.items()
    },
    'root': {'handlers': ['console'], 'level': 'INFO'},
}
