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
         name='order-list'
    ),
    path('orders',
        CartViewSet.as_view({'get': 'list'}),
        name='cart-viewset'
    ),
    path('add_item',
        CartViewSet.as_view({'post': 'add_item'}),
        name='cart-viewset'
    ),
    path('update_item/<str:pk>',
        CartViewSet.as_view({'put': 'update_item'}),
        name='cart-viewset'
    ),
    path('remove_item/<str:pk>',
        CartViewSet.as_view({'delete': 'remove_item'}),
        name='cart-viewset'
    ),
    path('checkout',
        CartViewSet.as_view({'post': 'checkout'}),
        name='cart-viewset'
    ),
    path('list', 
         OrderListView.as_view(), 
         name='order-create'
    ),
    path('<str:pk>', 
         OrderDetailView.as_view(), 
         name='order-detail'
    ),
    path('<str:pk>/update', 
         OrderUpdateView.as_view(), 
         name='order-update'
    ),
    path('<str:pk>/delete', 
         OrderDeleteView.as_view(), 
         name='order-delete'
    ),
]
