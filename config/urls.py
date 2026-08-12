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

from apps.flutter.views import VisitCardView, BankCardView
from config.views import (
    CSRFFailureView, SecurityHeadersView, RateLimitView, 
    HealthCheckView, LivenessView, ReadinessView,
    SecurityAuditView, ApiIndexView
)
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path(
        'admin/',
        admin.site.urls,
    ),
    # Health endpoints
    path('health/', HealthCheckView.as_view(), name='health_check'),
    path('health', HealthCheckView.as_view(), name='health_check_no_slash'),
    path('livez', LivenessView.as_view(), name='liveness'),
    path('livez/', LivenessView.as_view(), name='liveness_slash'),
    path('readyz', ReadinessView.as_view(), name='readiness'),
    path('readyz/', ReadinessView.as_view(), name='readiness_slash'),
    # API schema & docs
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/v1/health/', HealthCheckView.as_view(), name='api_health_check'),
    path('api/v1/', ApiIndexView.as_view(), name='api_index'),
    path(
        '',
        include('apps.index.urls'),
    ),
    path(
        'bank/share/<str:pk>',
        BankCardView.as_view()
    ),
    path(
        'api/v1/category/',
        include('apps.category.urls.general_urls'),
    ),
    path(
        'api/v1/info/',
        include('apps.information.urls.general_urls'),
    ),
    # Canonical public mobile API. Keep the root aliases below temporarily
    # for compatibility with already-issued links.
    path(
        'api/v1/',
        include('apps.flutter.urls', namespace='flutter_api'),
    ),
    path(
        'api/v1/region/',
        include('apps.region.urls.general_urls'),
    ),
    path(
        'api/v1/owner/market/',
        include('apps.market.urls.owner_urls'),
    ),
    path(
        'api/v1/owner/product/',
        include('apps.product.urls.owner_urls'),
    ),
    path(
        'api/v1/user/comment/',
        include('apps.comment.urls'),
    ),
    path(
        'api/v1/user/market/',
        include('apps.market.urls.user_urls'),
    ),
    path(
        'api/v1/user/',
        include('apps.users.urls.user_urls'),
    ),
    # discount
    path(
        'api/v1/discount/',
        include('apps.discount.urls'),
    ),
    # sms
    path(
        'api/v1/sms/admin/',
        include('apps.sms.urls.admin'),
    ),
    path(
        'api/v1/sms/owner/',
        include('apps.sms.urls.owner'),
    ),
    # reservation
    path(
        'api/v1/reservation/owner/',
        include('apps.reserve.urls.owner'),
    ),
    path(
        'api/v1/reservation/user/',
        include('apps.reserve.urls.user'),
    ),
    # price inquiry
    path(
        'api/v1/owner/inquiries/',
        include('apps.price_inquiry.urls.owner'),
    ),
    path(
        'api/v1/user/inquiries/',
        include('apps.price_inquiry.urls.user'),
    ),
    # advertisement
    path(
        'api/v1/advertisements/',
        include('apps.advertise.urls.user'),
    ),
    # affiliate
    path(
        'api/v1/owner/affiliate/',
        include('apps.affiliate.urls.owner'),
    ),
    path(
        'api/v1/user/affiliate/',
        include('apps.affiliate.urls.user'),
    ),
    # wallet
    path(
        'api/v1/wallet/',
        include('apps.wallet.urls'),
    ),
    # referral
    path(
        'api/v1/user/referral/',
        include('apps.referral.urls.user'),
    ),
    # payments
    path(
        'api/v1/user/payments/',
        include('apps.payment.urls.user'),
    ),
    # orders
    path(
        'api/v1/user/order/',
        include('apps.cart.urls.user'),
    ),
    path(
        'api/v1/owner/order/',
        include('apps.cart.urls.owner'),
    ),
    
    # analytics
    path(
        'api/v1/analytics/',
        include('apps.analytics.urls'),
    ),
    
    # notification
    path('', include('apps.notification.urls')),
    
    # chat
    path('', include('apps.chat.urls')),
    
    # Security endpoints
    path('security/audit/', SecurityAuditView.as_view(), name='security_audit'),
    path('csrf-failure/', CSRFFailureView.as_view(), name='csrf_failure'),
    path('rate-limit/', RateLimitView.as_view(), name='rate_limit'),

    # Legacy unversioned aliases for public mobile links.
    path('', include('apps.flutter.urls')),
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

# Place dynamic catch-all business route at the end to avoid swallowing other routes
urlpatterns += [
    path(
        '<str:business_id>',
        VisitCardView.as_view()
    ),
]
