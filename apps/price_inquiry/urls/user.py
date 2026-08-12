from django.urls import path
from apps.price_inquiry.views.user import (
    InquiryCreateView,
    InquiryUpdateView,
    InquiryDeleteView,
    InquiryImageUploadView,
    InquirySendSetView,
    InquiryListView,
    InquiryDetailView,
    InquiryExpiryRenewView,
    InquiryAnswerListView,
    InquiryAnswerDetailView
)
app_name = 'user_inquiry'

urlpatterns = [
    path('', InquiryListView.as_view(), name='list-inquiry'),
    path('create/', InquiryCreateView.as_view(), name='create-inquiry'),
    path('<str:pk>/update/', InquiryUpdateView.as_view(), name='update-inquiry'),
    path('<str:pk>/delete/', InquiryDeleteView.as_view(), name='delete-inquiry'),
    path('<str:pk>/', InquiryDetailView.as_view(), name='inquiry-detail'),
    path('<str:pk>/image/', InquiryImageUploadView.as_view(), name='add-inquiry-image'),
    path('<str:pk>/send/', InquirySendSetView.as_view(), name='inquiry-send'),
    path('<str:pk>/expiry/', InquiryExpiryRenewView.as_view(), name='inquiry-expiry'),

    path('<str:inquiry_pk>/answers/', InquiryAnswerListView.as_view(), name='list-inquiry-answers'),
    path('<str:inquiry_pk>/answers/<str:pk>', InquiryAnswerDetailView.as_view(), name='inquiry-answer-detail'),
]
