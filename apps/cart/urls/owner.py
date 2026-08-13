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
         name='owner_order_verify'
    ),
    path('list',
         OrderListView.as_view(),
         name='owner_order_list'
    ),
    path('<str:pk>',
         OrderDetailView.as_view(),
         name='owner_order_detail'
    ),
]
