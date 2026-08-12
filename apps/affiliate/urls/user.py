from django.urls import path

from apps.affiliate.views.user import (
    ProductsForAffiliateListView,
    AffiliateProductDetailBeforeCreateView,
    AffiliateProductCreateView,
    AffiliateProductsListView,
    AffiliateProductDetailView,
    AffiliateProductUpdateView,
    AffiliateProductDeleteView,
    AffiliateProductThemeCreateAPIView,
    AffiliateProductThemeListAPIView,
    AffiliateProductThemeUpdateAPIView,
)

app_name = 'affiliate_user'

urlpatterns = [
    path(
        'products/',
        ProductsForAffiliateListView.as_view(),
        name='products',
    ),
    path(
        'products/<str:pk>',
        AffiliateProductDetailBeforeCreateView.as_view(),
        name='product-detail',
    ),
    path(
        'create/',
        AffiliateProductCreateView.as_view(),
        name='create',
    ),
    path(
        'list/<str:pk>/',
        AffiliateProductsListView.as_view(),
        name='list',
    ),
    path(
        '<str:pk>/',
        AffiliateProductDetailView.as_view(),
        name='detail',
    ),
    path(
        '<str:pk>/update/',
        AffiliateProductUpdateView.as_view(),
        name='update',
    ),
    path(
        '<str:pk>/delete/',
        AffiliateProductDeleteView.as_view(),
        name='delete',
    ),
    path(
        'theme/create/<str:pk>/',
        AffiliateProductThemeCreateAPIView.as_view(),
        name='theme-create',
    ),
    path(
        'theme/list/<str:pk>/',
        AffiliateProductThemeListAPIView.as_view(),
        name='theme-list',
    ),
    path(
        'theme/<str:pk>/update/',
        AffiliateProductThemeUpdateAPIView.as_view(),
        name='theme-update',
    ),
]
