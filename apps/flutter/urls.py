from django.urls import path
from apps.market.views.business_card import PublicBusinessCardView
from apps.flutter.views import (
    MarketDetailView,
    MarketProductThemesView,
    ProductDetailView,
    ProductBookmarkView,
    ProductLikeView,
    ProductReportView,
    MarketLikeView,
    MarketBookmarkView,
    MarketReportView,
    AdvertizeDetailView,
    VisitCardView,
)
app_name = 'flutter_urls'

urlpatterns = [
    path('card/<str:business_id>', PublicBusinessCardView.as_view(), name='business-card'),
    path('markets', MarketDetailView.as_view(), name='market-detail'),
    path('markets/<uuid:pk>/like', MarketLikeView.as_view(), name='market-like'),
    path('markets/<uuid:pk>/bookmark', MarketBookmarkView.as_view(), name='market-bookmark'),
    path('markets/<uuid:pk>/report', MarketReportView.as_view(), name='market-report'),
    path('markets/products', MarketProductThemesView.as_view(), name='market-product-themes'),
    path('products', ProductDetailView.as_view(), name='product-detail'),
    path('products/<uuid:pk>/like', ProductLikeView.as_view(), name='product-like'),
    path('products/<uuid:pk>/bookmark', ProductBookmarkView.as_view(), name='product-bookmark'),
    path('products/<uuid:pk>/report', ProductReportView.as_view(), name='product-report'),
    path('advertisements', AdvertizeDetailView.as_view(), name='advertise-detail'),
    path('visit/<str:business_id>', VisitCardView.as_view(), name='visit-card'),
]
