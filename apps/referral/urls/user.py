from django.urls import path
from apps.referral.views import (
    ReferalCreateView,
    ReferalListView,
    MarketInviteCreateView,
)

app_name = 'user_referral'

urlpatterns = [
    path(
        'create/',
        ReferalCreateView.as_view(),
        name='create-referral'
    ),
    path(
        'invites/',
        MarketInviteCreateView.as_view(),
        name='create-market-invite',
    ),
    path(
        '',
        ReferalListView.as_view(),
        name='list-referral'
    ),
]
