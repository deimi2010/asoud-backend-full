from django.urls import path
from apps.cart.views.owner import (
    OrderVerifyView,
    OrderListView,
    OrderDetailView,
)
app_name = 'owner_order'

urlpatterns = [
    path('verify', 
         OrderVerifyView.as_view(), 
         name='order-list'
    ),
    path('list', 
         OrderListView.as_view(), 
         name='order-create'
    ),
    path('<str:pk>', 
         OrderDetailView.as_view(), 
         name='order-detail'
    ),
]