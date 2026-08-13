import logging

from django.conf import settings

logger = logging.getLogger(__name__)


def firebase_app():
    if not settings.FIREBASE_ENABLED:
        return None
    import firebase_admin

    try:
        return firebase_admin.get_app()
    except ValueError:
        options = {}
        if settings.FIREBASE_PROJECT_ID:
            options['projectId'] = settings.FIREBASE_PROJECT_ID
        return firebase_admin.initialize_app(options=options)


def verify_app_check_token(token):
    app = firebase_app()
    if app is None:
        return None
    from firebase_admin import app_check

    return app_check.verify_token(token, app=app)
