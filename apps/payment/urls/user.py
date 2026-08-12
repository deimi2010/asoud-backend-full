from django.urls import path
from apps.payment.views import (
    PaymentCreateView,
    PaymentRedirectView,
    PaymentVerifyView,
    PaymentListView,
    PaymentDetailView
)

app_name = 'user_payment'

urlpatterns = [
    path(
        'create/',
        PaymentCreateView.as_view(),
        name='payment-create'
    ),
    path(
        'pay',
        PaymentRedirectView.as_view(),
        name='payment-redirect'
    ),
    path(
        'verify/',
        PaymentVerifyView.as_view(),
        name='payment-verify'
    ),
    path(
        '',
        PaymentListView.as_view(),
        name='payment-list'
    ),
    path(
        '<str:pk>/',
        PaymentDetailView.as_view(),
        name='payment-detail'
    ),
]