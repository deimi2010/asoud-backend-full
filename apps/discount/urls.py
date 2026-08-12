from django.urls import path

from apps.discount.views.owner import (
    DiscountCreateView,
    DiscountDetailView,
    DiscountListView,
    DiscountDeleteView
)
from apps.discount.views.user import (
    DiscountValidateView
)

app_name = 'discount'

urlpatterns = [
    path(
        'owner/create/',
        DiscountCreateView.as_view(),
        name='create',
    ),
    path(
        'owner/list/',
        DiscountListView.as_view(),
        name='list',
    ),
    path(
        'owner/delete/<str:pk>/',
        DiscountDeleteView.as_view(),
        name='delete',
    ),
    path(
        'owner/<str:pk>/',
        DiscountDetailView.as_view(),
        name='get',
    ),

    path(
        'user/validate/',
        DiscountValidateView.as_view(),
        name='validate',
    ),
]