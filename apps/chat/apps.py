"""
Chat App Configuration
"""

from django.apps import AppConfig


class ChatConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.chat'
    verbose_name = 'Chat & Support System'
    
    def ready(self):
        """Import signals when app is ready"""
        try:
            import apps.chat.signals
        except ImportError:
            pass