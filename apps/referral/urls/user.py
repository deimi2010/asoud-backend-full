from django.urls import path
from apps.referral.views import (
    ReferalCreateView,
    ReferalListView
)

app_name = 'user_referral'

urlpatterns = [
    path(
        'create/',
        ReferalCreateView.as_view(),
        name='create-referral'
    ),
    path(
        '',
        ReferalListView.as_view(),
        name='list-referral'
    ),
]