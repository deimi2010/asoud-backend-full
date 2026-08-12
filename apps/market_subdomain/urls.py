from django.urls import path
from apps.market_subdomain.views import (
    MarketDetailView,
    ProductListView,
    ProductDetailView,
)


app_name = 'subdomains'

urlpatterns = [
    path(
        '',
        MarketDetailView.as_view()
    ),
    path(
        'products',
        ProductListView.as_view()
    ),
    path(
        'products/<str:pk>',
        ProductDetailView.as_view()
    ),
]