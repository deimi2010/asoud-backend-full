from django.urls import path

from apps.market.views.business_card import (
    BusinessCardDetailView,
    BusinessCardLifecycleView,
    BusinessCardListCreateView,
)


urlpatterns = [
    path('', BusinessCardListCreateView.as_view(), name='list-create'),
    path('<uuid:pk>/', BusinessCardDetailView.as_view(), name='detail'),
    path(
        '<uuid:pk>/<str:action>/',
        BusinessCardLifecycleView.as_view(),
        name='lifecycle',
    ),
]
