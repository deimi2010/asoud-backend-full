from django.urls import path
from apps.price_inquiry.views.owner import (
    InquiryListView,
    InquiryDetailView,
    InquiryAnswerListView,
    InquiryAnswerCreateView,
    InquiryAnswerDetailView
)
app_name = 'owner_inquiry'

urlpatterns = [
    path('', InquiryListView.as_view(), name='list-inquiry-owner'),
    path('answers/', InquiryAnswerListView.as_view(), name='list-inquiry-answers-owner'),
    path('<str:pk>/', InquiryDetailView.as_view(), name='inquiry-detail-owner'),
    path('answers/create/', InquiryAnswerCreateView.as_view(), name='inquiry-answer-create'),
    path('answers/<str:pk>', InquiryAnswerDetailView.as_view(), name='inquiry-answer-detail-owner'),
]