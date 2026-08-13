"""
URL configuration for asoud project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.utils.translation import gettext_lazy as _

from config.views import (
    CSRFFailureView, RateLimitView,
    HealthCheckView, LivenessView, ReadinessView,
    SecurityAuditView, ApiIndexView
)
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path('admin/', admin.site.urls),

    # Health endpoints
    path('health/', HealthCheckView.as_view(), name='health_check'),
    path('livez', LivenessView.as_view(), name='liveness'),
    path('readyz', ReadinessView.as_view(), name='readiness'),

    # API schema & docs
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/v1/health/', HealthCheckView.as_view(), name='api_health_check'),
    path('api/v1/', ApiIndexView.as_view(), name='api_index'),

    # Public landing and pre-authentication entry points.
    path('', include('apps.core.public_urls')),

    # API role-based router
    path('api/v1/', include('apps.core.urls')),

    # Authenticated mobile storefront projection.
    path('api/v1/storefront/', include('apps.flutter.urls', namespace='flutter_api')),

    # Security endpoints
    path('security/audit/', SecurityAuditView.as_view(), name='security_audit'),
    path('csrf-failure/', CSRFFailureView.as_view(), name='csrf_failure'),
    path('rate-limit/', RateLimitView.as_view(), name='rate_limit'),
]

admin.site.site_header = _('Asoud Administration')
admin.site.index_title = _('Welcome to Asoud Admin')
admin.site.site_title = _('Asoud Admin')


from django.conf import settings
from django.conf.urls.static import static

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL,
        document_root=settings.STATIC_ROOT)
