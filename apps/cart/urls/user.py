from django.urls import path
from apps.cart.views.user import (
    OrderCreateView,
    OrderListView,
    OrderDetailView,
    OrderUpdateView,
    OrderDeleteView,
    CartViewSet,
)
app_name = 'user_order'

urlpatterns = [
    path('create',
         OrderCreateView.as_view(),
         name='order_create'
    ),
    path('orders',
        CartViewSet.as_view({'get': 'list'}),
        name='user_cart_list'
    ),
    path('add_item',
        CartViewSet.as_view({'post': 'add_item'}),
        name='user_cart_add_item'
    ),
    path('update_item/<str:pk>',
        CartViewSet.as_view({'put': 'update_item'}),
        name='user_cart_update_item'
    ),
    path('remove_item/<str:pk>',
        CartViewSet.as_view({'delete': 'remove_item'}),
        name='user_cart_remove_item'
    ),
    path('checkout',
        CartViewSet.as_view({'post': 'checkout'}),
        name='user_cart_checkout'
    ),
    path('list',
         OrderListView.as_view(),
         name='order_list'
    ),
    path('<str:pk>',
         OrderDetailView.as_view(),
         name='order_detail'
    ),
    path('<str:pk>/update',
         OrderUpdateView.as_view(),
         name='order_update'
    ),
    path('<str:pk>/delete',
         OrderDeleteView.as_view(),
         name='order_delete'
    ),
]
