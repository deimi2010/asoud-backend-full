"""
Analytics App Configuration
"""

from django.apps import AppConfig
from django.conf import settings


class AnalyticsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.analytics'
    verbose_name = 'Analytics & Machine Learning'
    
    def ready(self):
        """Import signal handlers when the app is ready"""
        if not getattr(settings, 'ANALYTICS_ENABLED', False):
            return
        import apps.analytics.signals  # noqa: F401

