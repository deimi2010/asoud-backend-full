from django.urls import path

from apps.product.views.owner_views import (
    ProductCreateAPIView,
    ProductDiscountCreateAPIView,
    ProductListAPIView,
    ProductDetailAPIView,
    ProductUpdateAPIView,
    ProductThemeCreateAPIView,
    ProductThemeListAPIView,
    ProductThemeUpdateAPIView,
    ProductThemeDeleteAPIView,
    ProductShippingCreateAPIView,
    ProductShippingListAPIView
)

app_name = 'product_owner'

urlpatterns = [
    path(
        'create/',
        ProductCreateAPIView.as_view(),
        name='create',
    ),
    path(
        'discount/create/<uuid:pk>/',
        ProductDiscountCreateAPIView.as_view(),
        name='discount-create'
    ),
    path(
        'ship/create/<uuid:pk>/',
        ProductShippingCreateAPIView.as_view(),
        name='ship-create'
    ),
    path(
        'ship/list/<uuid:pk>/',
        ProductShippingListAPIView.as_view(),
        name='ship-list'
    ),
    path(
        'list/<str:pk>/',
        ProductListAPIView.as_view(),
        name='list',
    ),
    path(
        'detail/<uuid:pk>/',
        ProductDetailAPIView.as_view(),
        name='detail',
    ),
    path('update/<uuid:pk>/', ProductUpdateAPIView.as_view(), name='update'),
    path(
        'theme/create/<uuid:pk>/',
        ProductThemeCreateAPIView.as_view(),
        name='theme-create',
    ),
    path(
        'theme/list/<uuid:pk>/',
        ProductThemeListAPIView.as_view(),
        name='theme-list',
    ),
    path(
        'theme/update/<uuid:pk>/',
        ProductThemeUpdateAPIView.as_view(),
        name='theme-update',
    ),
    path(
        'theme/delete/<uuid:pk>/',
        ProductThemeDeleteAPIView.as_view(),
        name='theme-delete',
    ),
]
