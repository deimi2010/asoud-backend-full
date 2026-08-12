from django.urls import path

from apps.market.views.user_views import (
    MarketListAPIView,
    PublicMarketListAPIView,
    MarketReportAPIView,
    MarketBookmarkListAPIView,
    MarketBookmarkUpdateAPIView,
)
from apps.market.views.market_schedule import MarketScheduleUserListView

app_name = 'market_user'

urlpatterns = [
    path(
        'list/',
        MarketListAPIView.as_view(),
        name='list',
    ),
    path(
        'public/list/',
        PublicMarketListAPIView.as_view(),
        name='public-list',
    ),
    path(
        'report/<str:pk>/',
        MarketReportAPIView.as_view(),
        name='report',
    ),
    path(
        'bookmark/',
        MarketBookmarkListAPIView.as_view(),
        name='bookmark-list',
    ),
    path(
        'bookmark/<uuid:pk>/',
        MarketBookmarkUpdateAPIView.as_view(),
        name='bookmark-update',
    ),

    path(
        'schedule/<uuid:pk>/',
        MarketScheduleUserListView.as_view(),
        name='schedule-list',
    ),
]
