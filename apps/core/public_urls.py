from django.urls import include, path

from apps.flutter.views import BankCardView
from apps.referral.views import MarketInviteResolveView

app_name = 'public_api'

urlpatterns = [
    # Public landing page and storefront entry points.
    path('', include('apps.index.urls')),
    path('invite/<uuid:token>/', MarketInviteResolveView.as_view(), name='invite-resolve'),
    path('bank/share/<str:pk>', BankCardView.as_view(), name='bank-share'),
]
