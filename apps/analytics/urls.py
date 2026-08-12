from django.conf import settings
from django.urls import path


urlpatterns = []

if getattr(settings, 'ANALYTICS_ENABLED', False):
    from .views import (
        AnalyticsEventListView,
        DashboardView,
        OwnerProductForecastView,
        OwnerProductsView,
        OwnerSummaryView,
        OwnerTimeSeriesView,
        PlatformDashboardView,
        PlatformTimeSeriesView,
        PlatformTopMarketsView,
        PlatformTopProductsView,
        ProductRecommendationsView,
        SimilarProductsView,
        UserSessionListView,
    )

    urlpatterns = [
        path('dashboard/', DashboardView.as_view(), name='analytics-dashboard'),
        path('platform/dashboard/', PlatformDashboardView.as_view(), name='analytics-platform-dashboard'),
        path('platform/time-series/', PlatformTimeSeriesView.as_view(), name='analytics-platform-time-series'),
        path('platform/top-products/', PlatformTopProductsView.as_view(), name='analytics-platform-top-products'),
        path('platform/top-markets/', PlatformTopMarketsView.as_view(), name='analytics-platform-top-markets'),
        path('platform/events/', AnalyticsEventListView.as_view(), name='analytics-events'),
        path('platform/sessions/', UserSessionListView.as_view(), name='analytics-sessions'),
        path('owner/summary/', OwnerSummaryView.as_view(), name='analytics-owner-summary'),
        path('owner/time-series/', OwnerTimeSeriesView.as_view(), name='analytics-owner-time-series'),
        path('owner/products/', OwnerProductsView.as_view(), name='analytics-owner-products'),
        path('owner/products/<uuid:product_id>/forecast/', OwnerProductForecastView.as_view(), name='analytics-owner-forecast'),
        path('recommendations/products/', ProductRecommendationsView.as_view(), name='analytics-recommendations'),
        path('recommendations/similar/<uuid:product_id>/', SimilarProductsView.as_view(), name='analytics-similar-products'),
    ]
