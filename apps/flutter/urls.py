from django.urls import path
from apps.flutter.views import (
    MarketDetailView,
    MarketProductThemesView,
    ProductDetailView,
    ProductBookmarkView,
    ProductLikeView,
    ProductReportView,
    AdvertizeDetailView,
    VisitCardView,
)
app_name = 'flutter_urls'

urlpatterns = [
    path('markets', MarketDetailView.as_view(), name='market-detail'),
    path('markets/products', MarketProductThemesView.as_view(), name='market-product-themes'),
    path('products', ProductDetailView.as_view(), name='product-detail'),
    path('products/<uuid:pk>/like', ProductLikeView.as_view(), name='product-like'),
    path('products/<uuid:pk>/bookmark', ProductBookmarkView.as_view(), name='product-bookmark'),
    path('products/<uuid:pk>/report', ProductReportView.as_view(), name='product-report'),
    path('advertisements', AdvertizeDetailView.as_view(), name='advertise-detail'),
    path('visit/<str:business_id>', VisitCardView.as_view(), name='visit-card'),
]
