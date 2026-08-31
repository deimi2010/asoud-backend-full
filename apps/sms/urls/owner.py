from django.urls import path

from apps.sms.views.owner import (
    LineListView, 
    TemplateListView,
    BulkSmsView,
    PatternSmsView
)
from apps.sms.views.owner import (
    CampaignDetailView, CampaignListCreateView, CampaignPayView,
    ContactExcelUploadView, ContactListCreateView, SmsDashboardView,
)

app_name = 'sms_owner'

urlpatterns = [
    path('dashboard/', SmsDashboardView.as_view(), name='dashboard'),
    path('line/', LineListView.as_view(), name='list-lines'),
    path('template/', TemplateListView.as_view(), name='list-templates'),
    path('send/bulk/', BulkSmsView.as_view(), name='bulk-sms'),
    path('send/pattern/', PatternSmsView.as_view(), name='pattern-sms'),
    path('contacts/', ContactListCreateView.as_view(), name='contacts'),
    path('contacts/excel/', ContactExcelUploadView.as_view(), name='contacts-excel'),
    path('campaigns/', CampaignListCreateView.as_view(), name='campaigns'),
    path('campaigns/<uuid:pk>/', CampaignDetailView.as_view(), name='campaign-detail'),
    path('campaigns/<uuid:pk>/pay/', CampaignPayView.as_view(), name='campaign-pay'),
]
