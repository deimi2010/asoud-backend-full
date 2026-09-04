from django.apps import AppConfig


class MarketConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.market'

    def ready(self):
        from apps.market import signals  # noqa: F401
