from django.urls import path

from apps.sms.views.owner import (
    LineListView, 
    TemplateListView,
    BulkSmsView,
    PatternSmsView
)

app_name = 'sms_owner'

urlpatterns = [
    path('line/', LineListView.as_view(), name='list-lines'),
    path('template/', TemplateListView.as_view(), name='list-templates'),
    path('send/bulk/', BulkSmsView.as_view(), name='bulk-sms'),
    path('send/pattern/', PatternSmsView.as_view(), name='pattern-sms'),
]
