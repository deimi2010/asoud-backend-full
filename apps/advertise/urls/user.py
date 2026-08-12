from django.urls import path
from apps.advertise.views.user import (
    AdvertiseCreateView,
    AdvertiseListView,
    AdvertiseDetailView,
    AdvertiseOwnListView,
    AdvertiseUpdateView,
    AdvertiseDeleteView,
    AdvertisePaymentView
)
app_name = 'advertisement_urls'

urlpatterns = [
    path('', AdvertiseListView.as_view(), name='advertise-list'),
    path('payment', AdvertisePaymentView.as_view(), name='advertise-payment'),
    path('create', AdvertiseCreateView.as_view(), name='advertise-create'),
    path('self', AdvertiseOwnListView.as_view(), name='advertise-self-list'),
    path('<str:pk>', AdvertiseDetailView.as_view(), name='advertise-detail'),
    path('<str:pk>/update', AdvertiseUpdateView.as_view(), name='advertise-update'),
    path('<str:pk>/delete', AdvertiseDeleteView.as_view(), name='advertise-delete'),
]